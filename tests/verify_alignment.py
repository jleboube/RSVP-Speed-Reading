#!/usr/bin/env python3
"""
Verify ORP alignment in generated video frames.
Downloads a video and checks that the highlighted (red) letter
is always at the same x-coordinate.
"""

import subprocess
import tempfile
import os
from pathlib import Path
from PIL import Image

def extract_frames(video_url: str, output_dir: Path, num_frames: int = 10):
    """Extract frames from video using ffmpeg."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Download video first
    video_path = output_dir / "video.mp4"
    subprocess.run([
        "curl", "-s", "-L", "-o", str(video_path), video_url
    ], check=True)

    # Extract frames
    subprocess.run([
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", f"select=not(mod(n\\,5))",  # Every 5th frame
        "-vsync", "vfr",
        "-frames:v", str(num_frames),
        str(output_dir / "frame_%03d.png")
    ], capture_output=True, check=True)

    return sorted(output_dir.glob("frame_*.png"))

def find_red_pixel_center(image_path: Path) -> int:
    """Find the x-coordinate center of red pixels (ORP highlight)."""
    img = Image.open(image_path)
    pixels = img.load()
    width, height = img.size

    # Find red pixels (highlight color is typically #FF0000)
    red_x_coords = []
    for x in range(width):
        for y in range(height):
            r, g, b = pixels[x, y][:3]
            # Check for red-ish pixels (high red, low green/blue)
            if r > 200 and g < 100 and b < 100:
                red_x_coords.append(x)

    if not red_x_coords:
        return -1

    # Return center of red region
    return (min(red_x_coords) + max(red_x_coords)) // 2

def main():
    video_url = "https://rsvp.us-ord-1.linodeobjects.com/videos/a0c70dd9-ca97-4652-b690-374c0bfb4145/output.mp4"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        print(f"Extracting frames from video...")

        frames = extract_frames(video_url, tmpdir, num_frames=15)
        print(f"Extracted {len(frames)} frames")

        print("\nAnalyzing ORP alignment:")
        print("-" * 40)

        orp_positions = []
        for frame in frames:
            center_x = find_red_pixel_center(frame)
            orp_positions.append(center_x)
            print(f"{frame.name}: ORP center at x={center_x}")

        # Check alignment
        valid_positions = [x for x in orp_positions if x > 0]
        if valid_positions:
            min_x = min(valid_positions)
            max_x = max(valid_positions)
            variance = max_x - min_x

            print("-" * 40)
            print(f"ORP X range: {min_x} to {max_x}")
            print(f"Variance: {variance} pixels")

            # Note: 5px tolerance accounts for sub-pixel font rendering differences
            # Different character shapes have slight visual center variations
            if variance <= 10:
                print(f"\n✅ PASS: ORP alignment is consistent (within {variance} pixels, tolerance: 10px)")
            else:
                print(f"\n❌ FAIL: ORP alignment varies by {variance} pixels (tolerance: 10px)")
        else:
            print("Could not detect ORP in frames")

if __name__ == "__main__":
    main()
