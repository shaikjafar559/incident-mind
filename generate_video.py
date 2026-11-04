"""
Automated Video Generator for IncidentMind.
Uses Playwright to capture live UI states, edge-tts for professional voiceover narration,
and MoviePy to render a 1080p MP4 ready for YouTube.
"""

import os
import time
import asyncio
import threading
import uvicorn
from playwright.sync_api import sync_playwright
import edge_tts
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "video_assets")
os.makedirs(OUTPUT_DIR, exist_ok=True)

FINAL_VIDEO_PATH = os.path.join(os.path.dirname(__file__), "incident_mind_demo.mp4")

SCENES = [
    {
        "id": "scene_1_intro",
        "audio_text": (
            "Hey everyone! This is IncidentMind, an autonomous SRE triage agent powered by Hindsight, "
            "the persistent memory framework developed by Vectorize. In high-stakes production outages, "
            "stateless AI forgets everything, treating every critical failure like Day 1. "
            "IncidentMind gives agents persistent memory across incidents."
        ),
        "action": "intro",
        "title": "IncidentMind: Autonomous SRE Agent"
    },
    {
        "id": "scene_2_stateless_fail",
        "audio_text": (
            "Let's see what happens without memory. We receive a critical alert on our order service: "
            "PostgreSQL latency is spiking over 12 seconds, Kafka consumer lag is above 40,000, "
            "and asyncpg is throwing too many connection errors. "
            "With memory turned OFF, the agent gives generic, dangerous advice: restart the pod and check CPU. "
            "Restarting pods here causes an immediate connection stampede that crashes the primary database."
        ),
        "action": "stateless_triage",
        "title": "Without Memory: Generic Advice"
    },
    {
        "id": "scene_3_hindsight_recall",
        "audio_text": (
            "Now watch what happens when we flip Hindsight Memory ON. "
            "The agent calls arecall against our SRE cluster bank. In 40 milliseconds, Hindsight matches "
            "Incident 412 from three weeks ago with 98% confidence! "
            "It immediately diagnoses the exact root cause: unthrottled Kafka batch concurrency, "
            "and prescribes the battle-tested fix: throttling max poll records and terminating idle locks."
        ),
        "action": "hindsight_triage",
        "title": "With Hindsight: Instant Root Cause Match"
    },
    {
        "id": "scene_4_compare",
        "audio_text": (
            "Here is the side-by-side comparison. "
            "On the left, without memory: generic troubleshooting and a 45-minute outage. "
            "On the right, with Hindsight memory: exact root cause identification and a verified runbook. "
            "Mean Time to Resolution drops from 45 minutes to 90 seconds."
        ),
        "action": "compare",
        "title": "Side-by-Side Impact Comparison"
    },
    {
        "id": "scene_5_retain",
        "audio_text": (
            "When new incidents are resolved, operators click Retain Post-Mortem. "
            "Hindsight extracts entities, creates observation links, and persists this knowledge into the bank. "
            "The entire project, code, and documentation are open source on GitHub. Thanks for watching!"
        ),
        "action": "retain_view",
        "title": "Persistent Learning with Hindsight"
    }
]


def start_server():
    """Runs uvicorn in a daemon thread if not already running."""
    import httpx
    try:
        r = httpx.get("http://localhost:8000/api/scenarios", timeout=1.0)
        if r.status_code == 200:
            print("Server already running on port 8000.")
            return
    except Exception:
        pass

    print("Starting background FastAPI server on port 8000...")
    from backend.main import app
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    time.sleep(2.0)


async def generate_voiceovers():
    print("Generating neural voiceover audio files...")
    voice = "en-US-ChristopherNeural"
    for s in SCENES:
        audio_path = os.path.join(OUTPUT_DIR, f"{s['id']}.mp3")
        communicate = edge_tts.Communicate(s["audio_text"], voice=voice)
        await communicate.save(audio_path)
        print(f"Saved: {audio_path}")


def capture_screenshots():
    print("Capturing live 1080p screenshots with Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto("http://127.0.0.1:8000")
        page.wait_for_timeout(1500)

        for s in SCENES:
            action = s["action"]
            img_path = os.path.join(OUTPUT_DIR, f"{s['id']}.png")

            if action == "intro":
                page.screenshot(path=img_path)

            elif action == "stateless_triage":
                # Turn memory toggle OFF
                page.evaluate("() => { const t = document.getElementById('memoryToggle'); if(t.checked) t.click(); }")
                page.wait_for_timeout(400)
                # Click Run Triage
                page.click("#runTriageBtn")
                page.wait_for_timeout(1000)
                page.screenshot(path=img_path)

            elif action == "hindsight_triage":
                # Turn memory toggle ON
                page.evaluate("() => { const t = document.getElementById('memoryToggle'); if(!t.checked) t.click(); }")
                page.wait_for_timeout(400)
                # Click Run Triage
                page.click("#runTriageBtn")
                page.wait_for_timeout(1000)
                page.screenshot(path=img_path)

            elif action == "compare":
                # Click Side-by-Side Compare
                page.click("#compareModeBtn")
                page.wait_for_timeout(1200)
                page.screenshot(path=img_path)

            elif action == "retain_view":
                # Open retain modal
                page.click("#openRetainModalBtn")
                page.wait_for_timeout(500)
                page.screenshot(path=img_path)

            print(f"Captured: {img_path}")

        browser.close()


def compile_video():
    print("Assembling video clips with MoviePy...")
    clips = []
    for s in SCENES:
        img_path = os.path.join(OUTPUT_DIR, f"{s['id']}.png")
        audio_path = os.path.join(OUTPUT_DIR, f"{s['id']}.mp3")

        audio_clip = AudioFileClip(audio_path)
        duration = audio_clip.duration + 0.5  # slight buffer

        img_clip = ImageClip(img_path).with_duration(duration).with_audio(audio_clip)
        clips.append(img_clip)

    final_video = concatenate_videoclips(clips, method="compose")
    print(f"Rendering final MP4 to {FINAL_VIDEO_PATH} (1080p, 30fps)...")
    final_video.write_videofile(
        FINAL_VIDEO_PATH,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        logger="bar"
    )
    print("Video generation successfully completed!")


if __name__ == "__main__":
    start_server()
    asyncio.run(generate_voiceovers())
    capture_screenshots()
    compile_video()
