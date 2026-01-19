import os
import re
import uuid
import shutil
import subprocess
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image, ImageDraw, ImageFont

app = FastAPI(title="RSVP Video Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMP_DIR = Path("/tmp/rsvp_videos")
TEMP_DIR.mkdir(exist_ok=True)

FONTS = {
    "arial": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "serif": "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
}


class VideoConfig(BaseModel):
    wpm: int = 300
    font: str = "arial"
    text_color: str = "#000000"
    bg_color: str = "#FFFFFF"
    highlight_color: str = "#FF0000"
    pause_on_punctuation: bool = True
    word_grouping: int = 1
    width: int = 1920
    height: int = 1080


def hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def find_optimal_fixation_point(word: str) -> int:
    """Find the optimal recognition point (ORP) in a word."""
    length = len(word)
    if length <= 1:
        return 0
    if length <= 5:
        return length // 3
    if length <= 9:
        return length // 3
    return length // 4


def get_display_duration(words: str, wpm: int, pause_on_punctuation: bool) -> float:
    """Calculate display duration for a word/phrase in seconds."""
    base_duration = 60.0 / wpm

    if pause_on_punctuation:
        if words.rstrip().endswith((".", "!", "?")):
            return base_duration * 2.5
        if words.rstrip().endswith((",", ";", ":")):
            return base_duration * 1.5

    word_count = len(words.split())
    return base_duration * max(1, word_count * 0.8)


def parse_text(text: str, word_grouping: int = 1) -> list[str]:
    """Parse text into word groups for display."""
    words = text.split()
    if word_grouping == 1:
        return words

    groups = []
    for i in range(0, len(words), word_grouping):
        group = " ".join(words[i : i + word_grouping])
        groups.append(group)
    return groups


def extract_text_from_file(file_path: Path, content_type: str) -> str:
    """Extract text from uploaded file."""
    if content_type == "text/plain" or file_path.suffix == ".txt":
        return file_path.read_text(encoding="utf-8", errors="ignore")

    if content_type == "text/markdown" or file_path.suffix == ".md":
        import markdown

        text = file_path.read_text(encoding="utf-8", errors="ignore")
        html = markdown.markdown(text)
        clean_text = re.sub(r"<[^>]+>", " ", html)
        return clean_text

    if (
        content_type == "application/pdf"
        or file_path.suffix == ".pdf"
    ):
        from PyPDF2 import PdfReader

        reader = PdfReader(str(file_path))
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)

    if (
        content_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        or file_path.suffix == ".docx"
    ):
        from docx import Document

        doc = Document(str(file_path))
        return "\n".join(para.text for para in doc.paragraphs)

    raise ValueError(f"Unsupported file type: {content_type}")


def create_frame(
    word: str,
    config: VideoConfig,
    frame_path: Path,
) -> None:
    """Create a single frame image with the word displayed."""
    bg_rgb = hex_to_rgb(config.bg_color)
    text_rgb = hex_to_rgb(config.text_color)
    highlight_rgb = hex_to_rgb(config.highlight_color)

    img = Image.new("RGB", (config.width, config.height), bg_rgb)
    draw = ImageDraw.Draw(img)

    font_path = FONTS.get(config.font, FONTS["arial"])
    font_size = min(config.width, config.height) // 8

    try:
        font = ImageFont.truetype(font_path, font_size)
    except OSError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), word, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (config.width - text_width) // 2
    y = (config.height - text_height) // 2

    orp = find_optimal_fixation_point(word.replace(" ", ""))

    char_x = x
    for i, char in enumerate(word):
        char_bbox = draw.textbbox((0, 0), char, font=font)
        char_width = char_bbox[2] - char_bbox[0]

        color = highlight_rgb if i == orp else text_rgb
        draw.text((char_x, y), char, font=font, fill=color)
        char_x += char_width

    center_line_y = y - 20
    draw.line(
        [(config.width // 2, center_line_y), (config.width // 2, center_line_y + 10)],
        fill=highlight_rgb,
        width=3,
    )

    img.save(frame_path, "PNG")


async def generate_video(
    text: str,
    config: VideoConfig,
    job_id: str,
) -> Path:
    """Generate RSVP video from text."""
    job_dir = TEMP_DIR / job_id
    frames_dir = job_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    words = parse_text(text, config.word_grouping)

    if len(words) > 100000:
        raise ValueError("Text exceeds 100,000 word limit")

    frame_data = []
    for i, word in enumerate(words):
        frame_path = frames_dir / f"frame_{i:06d}.png"
        duration = get_display_duration(word, config.wpm, config.pause_on_punctuation)
        create_frame(word, config, frame_path)
        frame_data.append((frame_path, duration))

    concat_file = job_dir / "concat.txt"
    with open(concat_file, "w") as f:
        for frame_path, duration in frame_data:
            f.write(f"file '{frame_path}'\n")
            f.write(f"duration {duration}\n")
        if frame_data:
            f.write(f"file '{frame_data[-1][0]}'\n")

    output_path = job_dir / "output.mp4"

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-vf", "format=yuv420p",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        str(output_path),
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {stderr.decode()}")

    for frame_path, _ in frame_data:
        frame_path.unlink(missing_ok=True)

    return output_path


def cleanup_job(job_id: str) -> None:
    """Clean up job directory after delay."""
    job_dir = TEMP_DIR / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "rsvp-video-generator"}


@app.post("/api/generate")
async def generate_rsvp_video(
    background_tasks: BackgroundTasks,
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    wpm: int = Form(300),
    font: str = Form("arial"),
    text_color: str = Form("#000000"),
    bg_color: str = Form("#FFFFFF"),
    highlight_color: str = Form("#FF0000"),
    pause_on_punctuation: bool = Form(True),
    word_grouping: int = Form(1),
):
    if not text and not file:
        raise HTTPException(status_code=400, detail="No text or file provided")

    job_id = str(uuid.uuid4())

    config = VideoConfig(
        wpm=max(100, min(5000, wpm)),
        font=font,
        text_color=text_color,
        bg_color=bg_color,
        highlight_color=highlight_color,
        pause_on_punctuation=pause_on_punctuation,
        word_grouping=max(1, min(3, word_grouping)),
    )

    if file:
        if file.size and file.size > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 5MB)")

        job_dir = TEMP_DIR / job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        file_ext = Path(file.filename or "").suffix or ".txt"
        temp_file = job_dir / f"upload{file_ext}"

        with open(temp_file, "wb") as f:
            content = await file.read()
            f.write(content)

        try:
            text = extract_text_from_file(temp_file, file.content_type or "")
        except Exception as e:
            cleanup_job(job_id)
            raise HTTPException(status_code=400, detail=f"Failed to parse file: {e}")

    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="No text content found")

    text = " ".join(text.split())

    word_count = len(text.split())
    if word_count > 100000:
        raise HTTPException(
            status_code=400,
            detail=f"Text exceeds 100,000 word limit (found {word_count} words)",
        )

    try:
        output_path = await generate_video(text, config, job_id)
    except Exception as e:
        cleanup_job(job_id)
        raise HTTPException(status_code=500, detail=f"Video generation failed: {e}")

    background_tasks.add_task(cleanup_after_delay, job_id, 3600)

    return {
        "job_id": job_id,
        "word_count": word_count,
        "download_url": f"/api/download/{job_id}",
    }


async def cleanup_after_delay(job_id: str, delay: int):
    await asyncio.sleep(delay)
    cleanup_job(job_id)


@app.get("/api/download/{job_id}")
async def download_video(job_id: str):
    output_path = TEMP_DIR / job_id / "output.mp4"

    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Video not found or expired")

    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename="rsvp_video.mp4",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
