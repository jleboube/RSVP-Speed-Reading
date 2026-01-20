import os
import re
import uuid
import shutil
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

from app.worker import celery_app, generate_video_task, cleanup_job
from app.storage import is_s3_enabled, video_exists, get_video_url

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

    if content_type == "application/pdf" or file_path.suffix == ".pdf":
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


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "rsvp-video-generator"}


@app.post("/api/generate")
async def generate_rsvp_video(
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
    """Submit a video generation job. Returns immediately with job ID."""
    if not text and not file:
        raise HTTPException(status_code=400, detail="No text or file provided")

    job_id = str(uuid.uuid4())

    config = {
        "wpm": max(100, min(5000, wpm)),
        "font": font,
        "text_color": text_color,
        "bg_color": bg_color,
        "highlight_color": highlight_color,
        "pause_on_punctuation": pause_on_punctuation,
        "word_grouping": max(1, min(3, word_grouping)),
        "width": 1920,
        "height": 1080,
    }

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

    # Submit to Celery worker - returns immediately
    task = generate_video_task.apply_async(args=[job_id, text, config], task_id=job_id)

    return {
        "job_id": job_id,
        "task_id": task.id,
        "word_count": word_count,
        "status": "processing",
        "status_url": f"/api/status/{job_id}",
    }


@app.get("/api/status/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a video generation job."""
    task = celery_app.AsyncResult(job_id)

    if task.state == "PENDING":
        return {
            "job_id": job_id,
            "status": "pending",
            "percent": 0,
            "message": "Job is queued...",
        }
    elif task.state == "PROGRESS":
        info = task.info or {}
        return {
            "job_id": job_id,
            "status": "processing",
            "percent": info.get("percent", 0),
            "current": info.get("current", 0),
            "total": info.get("total", 0),
            "message": info.get("status", "Processing..."),
        }
    elif task.state == "SUCCESS":
        result = task.result or {}
        return {
            "job_id": job_id,
            "status": "completed",
            "percent": 100,
            "download_url": result.get("download_url", f"/api/download/{job_id}"),
            "word_count": result.get("word_count", 0),
        }
    elif task.state == "FAILURE":
        return {
            "job_id": job_id,
            "status": "failed",
            "percent": 0,
            "message": str(task.info) if task.info else "Job failed",
        }
    else:
        return {
            "job_id": job_id,
            "status": task.state.lower(),
            "percent": 0,
        }


@app.get("/api/download/{job_id}")
async def download_video(job_id: str):
    """Download the generated video."""
    # Check S3 first if enabled
    if is_s3_enabled() and video_exists(job_id):
        s3_url = get_video_url(job_id)
        return RedirectResponse(url=s3_url, status_code=302)

    # Fall back to local file
    output_path = TEMP_DIR / job_id / "output.mp4"

    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Video not found or expired")

    return FileResponse(
        output_path,
        media_type="video/mp4",
        filename="rsvp_video.mp4",
    )


@app.delete("/api/job/{job_id}")
async def delete_job(job_id: str):
    """Delete a job and its files."""
    cleanup_job(job_id)
    return {"status": "deleted", "job_id": job_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
