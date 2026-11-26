# Why: Automated full-system workflow execution and video recorder using Playwright.
# Navigates the complete customer booking journey, AI assistant, 5-minute hold timer,
# dual mode switching, and administrative analytics calendar, outputting a high-definition video.

import asyncio
import os
import shutil
import glob
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

BASE_URL = "http://localhost:5173"
VIDEO_DIR = os.path.abspath("docs/videos")
FINAL_VIDEO_PATH = os.path.join(VIDEO_DIR, "stylify_workflow_demo.webm")


async def main():
    os.makedirs(VIDEO_DIR, exist_ok=True)
    temp_video_dir = os.path.join(VIDEO_DIR, "temp_rec")
    if os.path.exists(temp_video_dir):
        shutil.rmtree(temp_video_dir, ignore_errors=True)
    os.makedirs(temp_video_dir, exist_ok=True)

    print("[1/8] Launching browser with video recorder (1280x720)...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=temp_video_dir,
            record_video_size={"width": 1280, "height": 720},
        )
        page = await context.new_page()

        try:
            # ── SCENE 1: Landing Page & Dual Mode Header ──
            print("[2/8] Scene 1: Navigating to Landing Page & Mode Switcher...")
            await page.goto(f"{BASE_URL}/", wait_until="networkidle")
            await page.wait_for_timeout(2000)

            # Smooth scroll to show value propositions
            await page.evaluate("window.scrollBy({ top: 500, behavior: 'smooth' })")
            await page.wait_for_timeout(1500)
            await page.evaluate("window.scrollBy({ top: 500, behavior: 'smooth' })")
            await page.wait_for_timeout(1500)
            await page.evaluate("window.scrollTo({ top: 0, behavior: 'smooth' })")
            await page.wait_for_timeout(1000)

            # ── SCENE 2: Dual Mode Login Portal ──
            print("[3/8] Scene 2: Testing Dual Login Portals (Customer vs Admin)...")
            await page.goto(f"{BASE_URL}/login", wait_until="networkidle")
            await page.wait_for_timeout(1500)

            # Toggle Admin Mode tab
            admin_tab = page.locator("button:has-text('Admin Mode')")
            if await admin_tab.count() > 0:
                await admin_tab.first.click()
                await page.wait_for_timeout(1200)

            # Switch back to User Mode tab
            user_tab = page.locator("button:has-text('User Mode')")
            if await user_tab.count() > 0:
                await user_tab.first.click()
                await page.wait_for_timeout(1200)

            # Click Sign In as Customer
            sign_in_btn = page.locator("button:has-text('Sign In as Customer'), button:has-text('Sign In as')")
            if await sign_in_btn.count() > 0:
                await sign_in_btn.first.click()
                await page.wait_for_timeout(2000)

            # ── SCENE 3: Services Catalog & AI Booking Copilot ──
            print("[4/8] Scene 3: Exploring Catalog & Asking AI Assistant...")
            await page.goto(f"{BASE_URL}/services", wait_until="networkidle")
            await page.wait_for_timeout(2000)

            # Open AI Assistant Floating Chat
            chat_btn = page.locator("button[aria-label='Toggle AI Booking Assistant']")
            if await chat_btn.count() > 0:
                await chat_btn.click()
                await page.wait_for_timeout(1500)

                # Type a natural language booking request
                chat_input = page.locator("input[placeholder*='Balayage']")
                if await chat_input.count() > 0:
                    await chat_input.fill("I want a haircut tomorrow morning under $80")
                    await page.wait_for_timeout(800)
                    send_btn = page.locator("button[aria-label='Send message']")
                    await send_btn.click()
                    print("      Waiting for AI parsed suggestions...")
                    await page.wait_for_timeout(3500)

                # Close chat window
                close_chat_btn = page.locator("div:has-text('Stylify Copilot') button")
                if await close_chat_btn.count() > 0:
                    await close_chat_btn.last.click()
                else:
                    await page.keyboard.press("Escape")
                await page.wait_for_timeout(1000)

            # ── SCENE 4: 5-Step Collision-Free Booking Wizard ──
            print("[5/8] Scene 4: Booking Wizard with Conflict-Free Time Window...")
            await page.goto(f"{BASE_URL}/book", wait_until="networkidle")
            await page.wait_for_timeout(1500)

            # Step 1: Click next to date
            next_btn = page.locator("button:has-text('Next: Select Date')")
            if await next_btn.count() > 0:
                await next_btn.click()
                await page.wait_for_timeout(1500)

            # Step 2: Date & Preference with Conflict-Free Guarantee
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            date_input = page.locator("input[type='date']")
            if await date_input.count() > 0:
                await date_input.fill(tomorrow)
                await page.wait_for_timeout(800)

            # Select Morning filter
            morning_btn = page.locator("button:has-text('Morning')")
            if await morning_btn.count() > 0:
                await morning_btn.click()
                await page.wait_for_timeout(800)

            view_slots_btn = page.locator("button:has-text('View Exact Open Slots')")
            if await view_slots_btn.count() > 0:
                await view_slots_btn.click()
                await page.wait_for_timeout(2500)

            # Step 3: Slots with 1-on-1 Dedicated Time Range
            reserve_btn = page.locator("button:has-text('Select & Reserve')")
            if await reserve_btn.count() > 0:
                await reserve_btn.first.click()
                print("      Activated 5-minute pre-booking hold lock!")
                await page.wait_for_timeout(2500)

                # Step 4: Review & Confirm with 5-minute Hold Timer
                confirm_btn = page.locator("button:has-text('Confirm Booking')")
                if await confirm_btn.count() > 0:
                    await confirm_btn.click()
                    print("      Appointment confirmed!")
                    await page.wait_for_timeout(2500)

            # ── SCENE 5: Customer Appointments & Waitlist ──
            print("[6/8] Scene 5: Viewing Customer Bookings & Waitlist...")
            await page.goto(f"{BASE_URL}/my-bookings", wait_until="networkidle")
            await page.wait_for_timeout(2000)

            await page.goto(f"{BASE_URL}/waitlist", wait_until="networkidle")
            await page.wait_for_timeout(1500)

            # ── SCENE 6: Switching to Admin Mode via Navbar ──
            print("[7/8] Scene 6: Switching to Admin Mode (Real-Time Analytics & Calendar)...")
            admin_mode_btn = page.locator("header button:has-text('Admin Mode')")
            if await admin_mode_btn.count() > 0:
                await admin_mode_btn.first.click()
                await page.wait_for_timeout(2500)

            # View Admin Dashboard
            await page.goto(f"{BASE_URL}/admin/dashboard", wait_until="networkidle")
            await page.wait_for_timeout(2500)
            await page.evaluate("window.scrollBy({ top: 400, behavior: 'smooth' })")
            await page.wait_for_timeout(1500)
            await page.evaluate("window.scrollTo({ top: 0, behavior: 'smooth' })")
            await page.wait_for_timeout(1000)

            # View Admin Calendar (FullCalendar with Stylist Columns)
            await page.goto(f"{BASE_URL}/admin/calendar", wait_until="networkidle")
            await page.wait_for_timeout(2500)

            # View Admin Bookings Table
            await page.goto(f"{BASE_URL}/admin/bookings", wait_until="networkidle")
            await page.wait_for_timeout(2500)

        finally:
            print("[8/8] Finalizing video recording...")
            await page.close()
            await context.close()
            await browser.close()

            # Move and finalize recorded video
            webm_files = glob.glob(os.path.join(temp_video_dir, "*.webm"))
            if webm_files:
                shutil.copy2(webm_files[0], FINAL_VIDEO_PATH)
                print(f"SUCCESS! Video workflow saved cleanly to: {FINAL_VIDEO_PATH}")
                file_size_mb = os.path.getsize(FINAL_VIDEO_PATH) / (1024 * 1024)
                print(f"Video size: {file_size_mb:.2f} MB")
            else:
                print("No webm files found in temporary directory.")


if __name__ == "__main__":
    asyncio.run(main())
