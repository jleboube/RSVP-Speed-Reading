#!/usr/bin/env python3
"""
Automated tests for RSVP Video Generator.

Run with: python3 tests/test_video_generation.py

Prerequisites:
- Docker containers must be running (docker compose up -d)
- Playwright must be installed (pip install playwright && playwright install chromium)

Tests:
1. Text input video generation
2. TXT file upload
3. Various WPM speeds
4. Error handling for edge cases
"""

import os
import sys
import tempfile
import requests
from pathlib import Path

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


def test_text_generation(results: TestResult):
    """Test video generation from text input."""
    try:
        response = requests.post(
            f"{API_URL}/generate",
            data={
                "text": SAMPLE_TEXT,
                "wpm": 1000,  # Fast for quick test
                "font": "arial",
                "text_color": "#000000",
                "bg_color": "#FFFFFF",
                "highlight_color": "#FF0000",
                "pause_on_punctuation": "true",
                "word_grouping": "1",
            },
            timeout=120,
        )

        if response.status_code == 200:
            data = response.json()
            if "job_id" in data and "download_url" in data:
                # Verify video is downloadable
                video_response = requests.get(
                    f"{BASE_URL}{data['download_url']}",
                    timeout=10
                )
                if video_response.status_code == 200:
                    content_type = video_response.headers.get("content-type", "")
                    if "video" in content_type:
                        results.add_pass("Text generation")
                    else:
                        results.add_fail("Text generation", f"Wrong content type: {content_type}")
                else:
                    results.add_fail("Text generation", f"Download failed: {video_response.status_code}")
            else:
                results.add_fail("Text generation", "Missing job_id or download_url")
        else:
            results.add_fail("Text generation", f"Status {response.status_code}: {response.text[:200]}")
    except Exception as e:
        results.add_fail("Text generation", str(e))


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
                data={"wpm": "1000"},
                timeout=120,
            )

        os.unlink(temp_path)

        if response.status_code == 200:
            data = response.json()
            if "job_id" in data:
                results.add_pass("TXT file upload")
            else:
                results.add_fail("TXT file upload", "Missing job_id")
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
            data={
                "text": "Quick test at maximum speed",
                "wpm": "5000",
            },
            timeout=30,
        )

        if response.status_code == 200:
            results.add_pass("High WPM (5000)")
        else:
            results.add_fail("High WPM (5000)", f"Status {response.status_code}")
    except Exception as e:
        results.add_fail("High WPM (5000)", str(e))


def test_low_wpm(results: TestResult):
    """Test video generation at low WPM (100)."""
    try:
        response = requests.post(
            f"{API_URL}/generate",
            data={
                "text": "Quick test at minimum speed",
                "wpm": "100",
            },
            timeout=60,
        )

        if response.status_code == 200:
            results.add_pass("Low WPM (100)")
        else:
            results.add_fail("Low WPM (100)", f"Status {response.status_code}")
    except Exception as e:
        results.add_fail("Low WPM (100)", str(e))


def test_word_grouping(results: TestResult):
    """Test video generation with word grouping."""
    try:
        response = requests.post(
            f"{API_URL}/generate",
            data={
                "text": "Testing word grouping feature with multiple words per frame",
                "wpm": "1000",
                "word_grouping": "3",
            },
            timeout=30,
        )

        if response.status_code == 200:
            results.add_pass("Word grouping (3 words)")
        else:
            results.add_fail("Word grouping (3 words)", f"Status {response.status_code}")
    except Exception as e:
        results.add_fail("Word grouping (3 words)", str(e))


def test_custom_colors(results: TestResult):
    """Test video generation with custom colors."""
    try:
        response = requests.post(
            f"{API_URL}/generate",
            data={
                "text": "Testing custom colors",
                "wpm": "1000",
                "text_color": "#FFFFFF",
                "bg_color": "#000000",
                "highlight_color": "#00FF00",
            },
            timeout=30,
        )

        if response.status_code == 200:
            results.add_pass("Custom colors")
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

    print("\nGeneration Tests:")
    test_text_generation(results)
    test_txt_file_upload(results)

    print("\nSpeed Tests:")
    test_high_wpm(results)
    test_low_wpm(results)

    print("\nFeature Tests:")
    test_word_grouping(results)
    test_custom_colors(results)

    success = results.summary()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
