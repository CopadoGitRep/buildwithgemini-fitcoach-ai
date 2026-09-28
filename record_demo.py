import asyncio
import os
import sys
from google.cloud import storage
from playwright.async_api import async_playwright

FRONTEND_URL = "https://fitcoach-frontend-907641820480.us-east1.run.app"
STORAGE_BUCKET_NAME = "fitcoach-ai-media-qwiklabs-gcp-03-6fec44d0cd84"
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-03-6fec44d0cd84"
OUTPUT_DIR = "/config/.gemini/antigravity/brain/749a82c6-08df-4376-a5eb-84f300041b92"


async def record():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    video_dir = os.path.join(OUTPUT_DIR, "video_temp")
    os.makedirs(video_dir, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="/usr/bin/google-chrome",
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=video_dir,
            record_video_size={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        print(f"Navigating to {FRONTEND_URL}...")
        await page.goto(FRONTEND_URL, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # 1. First Prompt: What the app does best (Catalog / Exercise recommendation)
        print("Sending Prompt 1: Show me leg exercises from the catalog...")
        await page.click("button.chip:has-text('Leg Exercises')")
        
        # Wait for agent response bubble to complete loading
        print("Waiting for FitCoach AI response...")
        await page.wait_for_selector(".msg.agent .bubble", timeout=45000)
        await page.wait_for_timeout(6000)

        # 2. Second Richer Prompt: Tool call + Database logging + 1RM calculation
        print("Sending Prompt 2: Log my chest workout: Bench Press 3x10 at 135 lbs and calculate my 1RM...")
        await page.fill("#input", "Log my chest workout: Bench Press 3x10 at 135 lbs and calculate my 1RM for 135 lbs at 10 reps")
        await page.click("form button[type='submit']")

        print("Waiting for FitCoach AI second response...")
        await page.wait_for_timeout(20000)

        # Close page and context to finalize video recording
        video_path = await page.video.path()
        await page.close()
        await context.close()
        await browser.close()

        print(f"Raw recorded video path: {video_path}")
        
        # Move recorded video to artifact directory
        target_video = os.path.join(OUTPUT_DIR, "fitcoach_demo.webm")
        if os.path.exists(video_path):
            os.rename(video_path, target_video)
            print(f"Demo video saved to: {target_video}")

            # Upload to Cloud Storage bucket for public link
            storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
            bucket = storage_client.bucket(STORAGE_BUCKET_NAME)
            blob = bucket.blob("fitcoach_demo.webm")
            with open(target_video, "rb") as vf:
                blob.upload_from_file(vf, content_type="video/webm")
            
            public_url = f"https://storage.googleapis.com/{STORAGE_BUCKET_NAME}/fitcoach_demo.webm"
            print(f"Public video URL: {public_url}")


if __name__ == "__main__":
    asyncio.run(record())
