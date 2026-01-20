#!/usr/bin/env python3
"""
Verify the landing page RSVP demo shows ORP-centered text.
"""
import time
from playwright.sync_api import sync_playwright

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})

        # Navigate to landing page
        page.goto('http://localhost:47293')
        page.wait_for_load_state('networkidle')

        # Wait for the demo to cycle through a few words
        time.sleep(2)

        # Take screenshots of the RSVP demo area
        page.screenshot(path='/tmp/landing_demo.png', full_page=False)
        print("Screenshot saved to /tmp/landing_demo.png")

        # Wait and capture more frames
        for i in range(3):
            time.sleep(0.4)
            page.screenshot(path=f'/tmp/landing_demo_{i+1}.png', full_page=False)
            print(f"Screenshot {i+1} saved")

        browser.close()
        print("\nDone! Check /tmp/landing_demo*.png to verify ORP alignment.")

if __name__ == "__main__":
    main()
