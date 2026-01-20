import os
import re
import shutil
import subprocess
from pathlib import Path

from celery import Celery
from PIL import Image, ImageDraw, ImageFont

from app.storage import upload_video, get_video_url, is_s3_enabled

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "rsvp_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,  # Results expire after 1 hour
)

TEMP_DIR = Path("/tmp/rsvp_videos")
TEMP_DIR.mkdir(exist_ok=True)

FONTS = {
    "arial": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "serif": "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
}


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


def create_frame(word: str, config: dict, frame_path: Path) -> None:
    """Create a single frame image with the word displayed.

    The ORP (Optimal Recognition Point) character is always positioned
    at the exact center of the frame so the eye doesn't need to move.
    """
    bg_rgb = hex_to_rgb(config["bg_color"])
    text_rgb = hex_to_rgb(config["text_color"])
    highlight_rgb = hex_to_rgb(config["highlight_color"])

    width = config.get("width", 1920)
    height = config.get("height", 1080)

    img = Image.new("RGB", (width, height), bg_rgb)
    draw = ImageDraw.Draw(img)

    font_path = FONTS.get(config.get("font", "arial"), FONTS["arial"])
    font_size = min(width, height) // 8

    try:
        font = ImageFont.truetype(font_path, font_size)
    except OSError:
        font = ImageFont.load_default()

    # Find ORP position
    orp = find_optimal_fixation_point(word.replace(" ", ""))

    # Calculate the precise position of each character using textbbox
    # This gives us the actual rendered bounding box
    char_positions = []
    current_x = 0
    for i, char in enumerate(word):
        # Get the actual bounding box when drawn at current_x
        char_bbox = draw.textbbox((current_x, 0), char, font=font)
        char_width = char_bbox[2] - char_bbox[0]
        char_left = char_bbox[0]
        char_positions.append({
            'char': char,
            'left': char_left,
            'width': char_width,
            'center': char_left + char_width / 2,
            'advance': font.getlength(char)  # How far to move for next char
        })
        current_x += font.getlength(char)

    # The ORP character's center position (relative to drawing at x=0)
    if orp < len(char_positions):
        orp_center = char_positions[orp]['center']
    else:
        orp_center = 0

    # Position word so ORP character center is at screen center
    screen_center_x = width // 2
    word_start_x = screen_center_x - orp_center

    # Calculate vertical position (center the text height)
    bbox = draw.textbbox((0, 0), word, font=font)
    text_height = bbox[3] - bbox[1]
    y = (height - text_height) // 2

    # Draw each character individually for coloring
    char_x = word_start_x
    for i, char in enumerate(word):
        color = highlight_rgb if i == orp else text_rgb
        draw.text((char_x, y), char, font=font, fill=color)
        char_x += char_positions[i]['advance']

    # Draw center alignment marker above text
    center_line_y = y - 20
    draw.line(
        [(screen_center_x, center_line_y), (screen_center_x, center_line_y + 10)],
        fill=highlight_rgb,
        width=3,
    )

    img.save(frame_path, "PNG")


@celery_app.task(bind=True)
def generate_video_task(self, job_id: str, text: str, config: dict):
    """Celery task to generate RSVP video from text."""
    job_dir = TEMP_DIR / job_id
    frames_dir = job_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    word_grouping = config.get("word_grouping", 1)
    wpm = config.get("wpm", 300)
    pause_on_punctuation = config.get("pause_on_punctuation", True)

    words = parse_text(text, word_grouping)
    total_words = len(words)

    if total_words > 100000:
        raise ValueError("Text exceeds 100,000 word limit")

    # Update progress during frame generation
    frame_data = []
    for i, word in enumerate(words):
        frame_path = frames_dir / f"frame_{i:06d}.png"
        duration = get_display_duration(word, wpm, pause_on_punctuation)
        create_frame(word, config, frame_path)
        frame_data.append((str(frame_path), duration))

        # Update progress every 100 frames
        if i % 100 == 0:
            progress = int((i / total_words) * 80)  # 0-80% for frame generation
            self.update_state(
                state="PROGRESS",
                meta={
                    "current": i,
                    "total": total_words,
                    "percent": progress,
                    "status": f"Generating frames ({i}/{total_words})",
                },
            )

    # Create concat file for FFmpeg
    concat_file = job_dir / "concat.txt"
    with open(concat_file, "w") as f:
        for frame_path, duration in frame_data:
            f.write(f"file '{frame_path}'\n")
            f.write(f"duration {duration}\n")
        if frame_data:
            f.write(f"file '{frame_data[-1][0]}'\n")

    self.update_state(
        state="PROGRESS",
        meta={
            "current": total_words,
            "total": total_words,
            "percent": 85,
            "status": "Encoding video...",
        },
    )

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

    process = subprocess.run(cmd, capture_output=True)

    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {process.stderr.decode()}")

    # Clean up frames
    for frame_path, _ in frame_data:
        Path(frame_path).unlink(missing_ok=True)

    # Upload to S3 if enabled
    s3_key = None
    video_url = f"/api/download/{job_id}"

    if is_s3_enabled():
        self.update_state(
            state="PROGRESS",
            meta={
                "current": total_words,
                "total": total_words,
                "percent": 95,
                "status": "Uploading to cloud storage...",
            },
        )
        s3_key = upload_video(output_path, job_id)
        if s3_key:
            video_url = get_video_url(job_id, s3_key)
            # Remove local file after successful S3 upload
            output_path.unlink(missing_ok=True)

    return {
        "job_id": job_id,
        "word_count": total_words,
        "download_url": video_url,
        "s3_key": s3_key,
        "status": "completed",
    }


def cleanup_job(job_id: str) -> None:
    """Clean up job directory."""
    job_dir = TEMP_DIR / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)
