"""
S3-compatible object storage module.

Supports:
- Akamai/Linode Object Storage (production)
- MinIO (local development)
- AWS S3
"""

import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# S3 Configuration from environment
S3_ENDPOINT = os.environ.get("S3_ENDPOINT", "")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY", "")
S3_BUCKET = os.environ.get("S3_BUCKET", "rsvp")
S3_REGION = os.environ.get("S3_REGION", "us-ord-1")
S3_PUBLIC_URL = os.environ.get("S3_PUBLIC_URL", "")  # Optional custom public URL

# Check if S3 is configured
S3_ENABLED = bool(S3_ENDPOINT and S3_ACCESS_KEY and S3_SECRET_KEY)


def get_s3_client():
    """Create and return an S3 client."""
    if not S3_ENABLED:
        return None

    return boto3.client(
        "s3",
        endpoint_url=f"https://{S3_ENDPOINT}" if not S3_ENDPOINT.startswith("http") else S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION,
        config=Config(signature_version="s3v4"),
    )


def upload_video(local_path: Path, job_id: str) -> Optional[str]:
    """
    Upload a video file to S3.

    Returns the S3 key (path) if successful, None if S3 is not configured.
    """
    if not S3_ENABLED:
        return None

    client = get_s3_client()
    if not client:
        return None

    s3_key = f"videos/{job_id}/output.mp4"

    try:
        client.upload_file(
            str(local_path),
            S3_BUCKET,
            s3_key,
            ExtraArgs={
                "ContentType": "video/mp4",
                "ACL": "public-read",  # Make video publicly accessible
            },
        )
        return s3_key
    except ClientError as e:
        print(f"S3 upload error: {e}")
        return None


def get_video_url(job_id: str, s3_key: Optional[str] = None) -> Optional[str]:
    """
    Get the public URL for a video.

    Returns a public URL if S3 is configured and file exists.
    """
    if not S3_ENABLED:
        return None

    if not s3_key:
        s3_key = f"videos/{job_id}/output.mp4"

    # If custom public URL is set (e.g., CDN), use that
    if S3_PUBLIC_URL:
        return f"{S3_PUBLIC_URL.rstrip('/')}/{s3_key}"

    # Otherwise, construct the public URL from the bucket endpoint
    # For Linode/Akamai: https://bucket.endpoint/key
    return f"https://{S3_BUCKET}.{S3_ENDPOINT}/{s3_key}"


def get_presigned_url(job_id: str, s3_key: Optional[str] = None, expires_in: int = 3600) -> Optional[str]:
    """
    Generate a pre-signed URL for private bucket access.

    Args:
        job_id: The job ID
        s3_key: Optional S3 key, defaults to videos/{job_id}/output.mp4
        expires_in: URL expiration time in seconds (default 1 hour)

    Returns a pre-signed URL if S3 is configured.
    """
    if not S3_ENABLED:
        return None

    client = get_s3_client()
    if not client:
        return None

    if not s3_key:
        s3_key = f"videos/{job_id}/output.mp4"

    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET, "Key": s3_key},
            ExpiresIn=expires_in,
        )
        return url
    except ClientError as e:
        print(f"S3 presigned URL error: {e}")
        return None


def delete_video(job_id: str, s3_key: Optional[str] = None) -> bool:
    """
    Delete a video from S3.

    Returns True if successful or S3 not configured.
    """
    if not S3_ENABLED:
        return True

    client = get_s3_client()
    if not client:
        return True

    if not s3_key:
        s3_key = f"videos/{job_id}/output.mp4"

    try:
        client.delete_object(Bucket=S3_BUCKET, Key=s3_key)
        return True
    except ClientError as e:
        print(f"S3 delete error: {e}")
        return False


def video_exists(job_id: str, s3_key: Optional[str] = None) -> bool:
    """Check if a video exists in S3."""
    if not S3_ENABLED:
        return False

    client = get_s3_client()
    if not client:
        return False

    if not s3_key:
        s3_key = f"videos/{job_id}/output.mp4"

    try:
        client.head_object(Bucket=S3_BUCKET, Key=s3_key)
        return True
    except ClientError:
        return False


def ensure_bucket_exists() -> bool:
    """
    Ensure the S3 bucket exists. Creates it if it doesn't.

    Returns True if bucket exists or was created.
    """
    if not S3_ENABLED:
        return False

    client = get_s3_client()
    if not client:
        return False

    try:
        client.head_bucket(Bucket=S3_BUCKET)
        return True
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "404":
            # Bucket doesn't exist, try to create it
            try:
                client.create_bucket(Bucket=S3_BUCKET)
                print(f"Created S3 bucket: {S3_BUCKET}")
                return True
            except ClientError as create_error:
                print(f"Failed to create bucket: {create_error}")
                return False
        else:
            print(f"S3 bucket check error: {e}")
            return False


def is_s3_enabled() -> bool:
    """Check if S3 storage is enabled."""
    return S3_ENABLED
