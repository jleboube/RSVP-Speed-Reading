#!/usr/bin/env python3
"""
Verify the landing page RSVP demo at wider viewport.
"""
import time
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Test at wider viewport like user's screenshot
        page = browser.new_page(viewport={'width': 2560, 'height': 1440})

        page.goto('http://localhost:47293')
        page.wait_for_load_state('networkidle')

        time.sleep(1)

        for i in range(4):
            time.sleep(0.35)
            page.screenshot(path=f'/tmp/landing_wide_{i}.png', full_page=False)
            print(f"Wide screenshot {i} saved")

        browser.close()
        print("\nDone! Check /tmp/landing_wide_*.png")

if __name__ == "__main__":
    main()
