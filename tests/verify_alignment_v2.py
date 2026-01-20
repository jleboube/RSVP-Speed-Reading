#!/usr/bin/env python3
"""
Verify ORP alignment in generated video frames - detailed version.
"""

import subprocess
import tempfile
import os
from pathlib import Path
from PIL import Image

def extract_frames(video_url: str, output_dir: Path, num_frames: int = 20):
    """Extract frames from video using ffmpeg."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Download video first
    video_path = output_dir / "video.mp4"
    subprocess.run([
        "curl", "-s", "-L", "-o", str(video_path), video_url
    ], check=True)

    # Extract all frames (1 per word shown)
    subprocess.run([
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", f"select=not(mod(n\\,3))",  # Every 3rd frame
        "-vsync", "vfr",
        "-frames:v", str(num_frames),
        str(output_dir / "frame_%03d.png")
    ], capture_output=True, check=True)

    return sorted(output_dir.glob("frame_*.png"))

def analyze_red_pixels(image_path: Path) -> dict:
    """Analyze red pixels in detail."""
    img = Image.open(image_path)
    pixels = img.load()
    width, height = img.size

    red_x_coords = []
    for x in range(width):
        for y in range(height):
            r, g, b = pixels[x, y][:3]
            if r > 200 and g < 100 and b < 100:
                red_x_coords.append(x)

    if not red_x_coords:
        return {'min': -1, 'max': -1, 'center': -1, 'width': 0}

    min_x = min(red_x_coords)
    max_x = max(red_x_coords)
    center = (min_x + max_x) // 2

    return {
        'min': min_x,
        'max': max_x,
        'center': center,
        'width': max_x - min_x
    }

def main():
    video_url = "https://rsvp.us-ord-1.linodeobjects.com/videos/a0c70dd9-ca97-4652-b690-374c0bfb4145/output.mp4"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        print(f"Extracting frames from video...")

        frames = extract_frames(video_url, tmpdir, num_frames=26)
        print(f"Extracted {len(frames)} frames")

        print("\nDetailed ORP Analysis:")
        print("-" * 70)
        print(f"{'Frame':<15} {'Min X':<10} {'Max X':<10} {'Center':<10} {'Width':<10}")
        print("-" * 70)

        centers = []
        min_xs = []
        for frame in frames:
            info = analyze_red_pixels(frame)
            if info['center'] > 0:
                print(f"{frame.name:<15} {info['min']:<10} {info['max']:<10} {info['center']:<10} {info['width']:<10}")
                centers.append(info['center'])
                min_xs.append(info['min'])

        print("-" * 70)

        if centers:
            print(f"\nCenter X Statistics:")
            print(f"  Range: {min(centers)} to {max(centers)}")
            print(f"  Variance: {max(centers) - min(centers)} pixels")
            print(f"  Screen center: 960")

            print(f"\nMin X Statistics (left edge of ORP char):")
            print(f"  Range: {min(min_xs)} to {max(min_xs)}")
            print(f"  Variance: {max(min_xs) - min(min_xs)} pixels")

if __name__ == "__main__":
    main()
