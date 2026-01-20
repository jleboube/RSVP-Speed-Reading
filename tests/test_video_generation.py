#!/usr/bin/env python3
"""
Automated tests for RSVP Video Generator.

Run with: python3 tests/test_video_generation.py

Prerequisites:
- Docker containers must be running (docker compose up -d)

Tests:
1. Health check
2. Async job submission
3. Job status polling
4. Video download
5. Various WPM speeds
6. Error handling for edge cases
"""

import os
import sys
import time
import tempfile
import requests

# Configuration
BASE_URL = os.environ.get("RSVP_TEST_URL", "http://localhost:47293")
API_URL = f"{BASE_URL}/api"

# Test content
SAMPLE_TEXT = """
Speed reading is a fascinating skill that allows readers to consume text at
remarkable rates. RSVP, or Rapid Serial Visual Presentation, displays words
one at a time in a fixed position, eliminating eye movement across the page.
The Optimal Recognition Point helps readers focus on the best spot in each word.
"""


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_pass(self, name):
        self.passed += 1
        print(f"  ✅ {name}")

    def add_fail(self, name, error):
        self.failed += 1
        self.errors.append((name, error))
        print(f"  ❌ {name}: {error}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*50}")
        print(f"Results: {self.passed}/{total} tests passed")
        if self.errors:
            print("\nFailures:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
        return self.failed == 0


def wait_for_job(job_id: str, timeout: int = 60) -> dict:
    """Poll job status until completed or failed."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        response = requests.get(f"{API_URL}/status/{job_id}", timeout=5)
        if response.status_code != 200:
            raise Exception(f"Status check failed: {response.status_code}")

        status = response.json()
        if status.get("status") == "completed":
            return status
        elif status.get("status") == "failed":
            raise Exception(f"Job failed: {status.get('message', 'Unknown error')}")

        time.sleep(1)

    raise Exception(f"Job timed out after {timeout}s")


def test_health_check(results: TestResult):
    """Test that the API is healthy."""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            results.add_pass("Health check")
        else:
            results.add_fail("Health check", f"Status {response.status_code}")
    except Exception as e:
        results.add_fail("Health check", str(e))


def test_async_job_submission(results: TestResult):
    """Test that job submission returns immediately with job ID."""
    try:
        start_time = time.time()
        response = requests.post(
            f"{API_URL}/generate",
            data={"text": SAMPLE_TEXT, "wpm": 1000},
            timeout=10,
        )
        elapsed = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            if "job_id" in data and "status_url" in data:
                if elapsed < 5:  # Should return in under 5 seconds
                    results.add_pass("Async job submission (fast return)")
                else:
                    results.add_fail("Async job submission", f"Took {elapsed:.1f}s (should be <5s)")
            else:
                results.add_fail("Async job submission", "Missing job_id or status_url")
        else:
            results.add_fail("Async job submission", f"Status {response.status_code}")
    except Exception as e:
        results.add_fail("Async job submission", str(e))


def test_job_status_polling(results: TestResult):
    """Test job status endpoint returns progress."""
    try:
        # Submit a job
        response = requests.post(
            f"{API_URL}/generate",
            data={"text": SAMPLE_TEXT, "wpm": 1000},
            timeout=10,
        )
        data = response.json()
        job_id = data["job_id"]

        # Check status
        status_response = requests.get(f"{API_URL}/status/{job_id}", timeout=5)
        if status_response.status_code == 200:
            status = status_response.json()
            if "status" in status and "percent" in status:
                results.add_pass("Job status polling")
            else:
                results.add_fail("Job status polling", "Missing status or percent fields")
        else:
            results.add_fail("Job status polling", f"Status {status_response.status_code}")
    except Exception as e:
        results.add_fail("Job status polling", str(e))


def test_full_generation_flow(results: TestResult):
    """Test complete flow: submit -> poll -> download."""
    try:
        # Submit job
        response = requests.post(
            f"{API_URL}/generate",
            data={"text": SAMPLE_TEXT, "wpm": 2000},  # Fast for quick test
            timeout=10,
        )
        data = response.json()
        job_id = data["job_id"]

        # Wait for completion
        status = wait_for_job(job_id, timeout=60)

        # Download video
        download_url = status.get("download_url", f"/api/download/{job_id}")
        video_response = requests.get(f"{BASE_URL}{download_url}", timeout=10)

        if video_response.status_code == 200:
            content_type = video_response.headers.get("content-type", "")
            if "video" in content_type:
                results.add_pass("Full generation flow")
            else:
                results.add_fail("Full generation flow", f"Wrong content type: {content_type}")
        else:
            results.add_fail("Full generation flow", f"Download failed: {video_response.status_code}")
    except Exception as e:
        results.add_fail("Full generation flow", str(e))


def test_txt_file_upload(results: TestResult):
    """Test video generation from TXT file upload."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(SAMPLE_TEXT)
            temp_path = f.name

        with open(temp_path, 'rb') as f:
            response = requests.post(
                f"{API_URL}/generate",
                files={"file": ("test.txt", f, "text/plain")},
                data={"wpm": "2000"},
                timeout=10,
            )

        os.unlink(temp_path)

        if response.status_code == 200:
            data = response.json()
            job_id = data["job_id"]
            status = wait_for_job(job_id, timeout=60)
            if status.get("status") == "completed":
                results.add_pass("TXT file upload")
            else:
                results.add_fail("TXT file upload", f"Job status: {status.get('status')}")
        else:
            results.add_fail("TXT file upload", f"Status {response.status_code}")
    except Exception as e:
        results.add_fail("TXT file upload", str(e))


def test_empty_text_rejection(results: TestResult):
    """Test that empty text is rejected."""
    try:
        response = requests.post(
            f"{API_URL}/generate",
            data={"text": "   "},
            timeout=10,
        )

        if response.status_code == 400:
            results.add_pass("Empty text rejection")
        else:
            results.add_fail("Empty text rejection", f"Expected 400, got {response.status_code}")
    except Exception as e:
        results.add_fail("Empty text rejection", str(e))


def test_high_wpm(results: TestResult):
    """Test video generation at high WPM (5000)."""
    try:
        response = requests.post(
            f"{API_URL}/generate",
            data={"text": "Quick test at maximum speed", "wpm": "5000"},
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            status = wait_for_job(data["job_id"], timeout=30)
            if status.get("status") == "completed":
                results.add_pass("High WPM (5000)")
            else:
                results.add_fail("High WPM (5000)", f"Job status: {status.get('status')}")
        else:
            results.add_fail("High WPM (5000)", f"Status {response.status_code}")
    except Exception as e:
        results.add_fail("High WPM (5000)", str(e))


def test_custom_colors(results: TestResult):
    """Test video generation with custom colors."""
    try:
        response = requests.post(
            f"{API_URL}/generate",
            data={
                "text": "Testing custom colors",
                "wpm": "2000",
                "text_color": "#FFFFFF",
                "bg_color": "#000000",
                "highlight_color": "#00FF00",
            },
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            status = wait_for_job(data["job_id"], timeout=30)
            if status.get("status") == "completed":
                results.add_pass("Custom colors")
            else:
                results.add_fail("Custom colors", f"Job status: {status.get('status')}")
        else:
            results.add_fail("Custom colors", f"Status {response.status_code}")
    except Exception as e:
        results.add_fail("Custom colors", str(e))


def run_all_tests():
    """Run all tests and report results."""
    print("="*50)
    print("RSVP Video Generator - Automated Tests")
    print(f"Target: {BASE_URL}")
    print("="*50)
    print()

    results = TestResult()

    print("API Tests:")
    test_health_check(results)
    test_empty_text_rejection(results)

    print("\nAsync Flow Tests:")
    test_async_job_submission(results)
    test_job_status_polling(results)

    print("\nGeneration Tests:")
    test_full_generation_flow(results)
    test_txt_file_upload(results)

    print("\nFeature Tests:")
    test_high_wpm(results)
    test_custom_colors(results)

    success = results.summary()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
