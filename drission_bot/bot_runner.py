"""
DrissionPage Bot Runner — Real browser bot that browses your server.

Uses DrissionPage (Chromium-based, no WebDriver) to simulate a real browser
visiting your local server. All activity is captured and sent to the
detection engine for monitoring.

This bot:
1. Opens a real Chromium browser
2. Browses your DemoSite / local server
3. Clicks links, scrolls, fills forms
4. Records every action with timestamps, mouse positions, timing
5. Sends the activity session to the detection API for analysis

Usage:
    1. Start your server: dotnet run (in AISecutity folder)
    2. Run this bot: python drission_bot/bot_runner.py
"""

import json
import os
import random
import time
from datetime import datetime, timezone

import requests

# Target server (your AISecutity API)
TARGET_BASE = "http://localhost:5000"
DETECTION_API = f"{TARGET_BASE}/api/ban/analyze-and-ban"

# Pages to browse (simulating a real site)
PAGES = [
    "/",
    "/home",
    "/products",
    "/about",
    "/contact",
]

OUTPUT_DIR = "./drission_bot/activity_logs"


class ActivityRecorder:
    """Records all bot actions into the ActivitySession format."""

    def __init__(self, session_id: str, user_id: str):
        self.session_id = session_id
        self.user_id = user_id
        self.events = []
        self.start_time = time.time()

    def record(self, event_type: str, endpoint: str, mouse_x: int = 0, mouse_y: int = 0,
               mouse_speed: float = 0, has_curve: bool = False, duration_ms: int = 0,
               keyboard: dict = None):
        """Record a single activity event."""
        self.events.append({
            "sessionId": self.session_id,
            "userId": self.user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "eventType": event_type,
            "endpoint": endpoint,
            "durationMs": duration_ms,
            "mouse": {
                "x": mouse_x,
                "y": mouse_y,
                "speed": mouse_speed,
                "hasCurve": has_curve,
            } if mouse_x or mouse_y else None,
            "keyboard": keyboard,
        })

    def get_session(self) -> dict:
        """Get the full session in ActivitySession format."""
        return {
            "sessionId": self.session_id,
            "userId": self.user_id,
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
            "ipAddress": "127.0.0.1",
            "events": self.events,
        }


def run_bot_headless():
    """Run the bot in headless mode (no browser window) using HTTP requests.
    Falls back to this if Chrome is not available.
    """
    session_id = f"drission-bot-{int(time.time())}"
    user_id = "drission-user-001"
    recorder = ActivityRecorder(session_id, user_id)

    print(f"  Session: {session_id}")
    print(f"  Target:  {TARGET_BASE}")
    print(f"  Mode:    HTTP requests (headless)\n")

    # Simulate browsing behavior
    pages_to_visit = random.sample(PAGES, min(len(PAGES), 4)) + random.choices(PAGES, k=6)

    for i, page in enumerate(pages_to_visit):
        url = f"{TARGET_BASE}{page}"

        # Record navigation
        mouse_x = random.randint(100, 1200)
        mouse_y = random.randint(100, 800)
        speed = random.uniform(800, 1500)  # Bot-like: slightly fast

        start = time.time()
        try:
            resp = requests.get(url, timeout=5)
            duration = int((time.time() - start) * 1000)

            recorder.record(
                event_type="navigation",
                endpoint=page,
                mouse_x=mouse_x,
                mouse_y=mouse_y,
                mouse_speed=round(speed, 1),
                has_curve=random.random() < 0.3,  # Bot: rarely curves
                duration_ms=duration,
            )
            print(f"  [{i+1:2}/{len(pages_to_visit)}] GET {page} → {resp.status_code} ({duration}ms)")

        except requests.exceptions.ConnectionError:
            print(f"  [{i+1:2}/{len(pages_to_visit)}] GET {page} → CONNECTION REFUSED")
            recorder.record(
                event_type="navigation",
                endpoint=page,
                duration_ms=0,
            )

        # Bot-like delay: too consistent
        delay = random.gauss(0.8, 0.1)  # Very regular ~800ms
        time.sleep(max(0.2, delay))

        # Simulate some clicks/scrolls
        if random.random() < 0.5:
            recorder.record(
                event_type="click",
                endpoint=page,
                mouse_x=random.randint(200, 1000),
                mouse_y=random.randint(200, 600),
                mouse_speed=round(random.uniform(900, 1400), 1),
                has_curve=False,
                duration_ms=random.randint(50, 200),
            )
            time.sleep(random.gauss(0.5, 0.05))

        if random.random() < 0.3:
            recorder.record(
                event_type="scroll",
                endpoint=page,
                mouse_x=random.randint(400, 800),
                mouse_y=random.randint(300, 900),
                mouse_speed=round(random.uniform(600, 1000), 1),
                has_curve=False,
                duration_ms=random.randint(100, 500),
            )

    return recorder


def run_bot_with_drission():
    """Run the bot using DrissionPage with a real browser."""
    from DrissionPage import ChromiumPage, ChromiumOptions

    session_id = f"drission-bot-{int(time.time())}"
    user_id = "drission-user-001"
    recorder = ActivityRecorder(session_id, user_id)

    print(f"  Session: {session_id}")
    print(f"  Target:  {TARGET_BASE}")
    print(f"  Mode:    DrissionPage (real Chromium browser)\n")

    # Configure headless Chromium
    co = ChromiumOptions()
    co.headless()
    co.set_argument('--no-sandbox')
    co.set_argument('--disable-gpu')

    try:
        page = ChromiumPage(co)
    except Exception as e:
        print(f"  Failed to start Chromium: {e}")
        print(f"  Falling back to HTTP mode...\n")
        return run_bot_headless()

    pages_to_visit = random.sample(PAGES, min(len(PAGES), 4)) + random.choices(PAGES, k=6)

    for i, path in enumerate(pages_to_visit):
        url = f"{TARGET_BASE}{path}"

        start = time.time()
        try:
            page.get(url)
            duration = int((time.time() - start) * 1000)

            # Get page dimensions for realistic mouse positions
            mouse_x = random.randint(100, 1200)
            mouse_y = random.randint(100, 800)
            speed = random.uniform(800, 1500)

            recorder.record(
                event_type="navigation",
                endpoint=path,
                mouse_x=mouse_x,
                mouse_y=mouse_y,
                mouse_speed=round(speed, 1),
                has_curve=random.random() < 0.3,
                duration_ms=duration,
            )
            print(f"  [{i+1:2}/{len(pages_to_visit)}] Browse {path} ({duration}ms)")

        except Exception as e:
            print(f"  [{i+1:2}/{len(pages_to_visit)}] Error on {path}: {e}")
            recorder.record(event_type="navigation", endpoint=path, duration_ms=0)

        # Bot delay
        time.sleep(random.gauss(0.8, 0.1))

        # Click random elements
        if random.random() < 0.5:
            try:
                links = page.eles('tag:a')
                if links:
                    link = random.choice(links[:5])
                    recorder.record(
                        event_type="click",
                        endpoint=path,
                        mouse_x=random.randint(200, 1000),
                        mouse_y=random.randint(200, 600),
                        mouse_speed=round(random.uniform(900, 1400), 1),
                        has_curve=False,
                        duration_ms=random.randint(50, 200),
                    )
            except:
                pass

    try:
        page.quit()
    except:
        pass

    return recorder


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 70)
    print("  DRISSIONPAGE BOT RUNNER + ACTIVITY MONITOR")
    print("=" * 70)

    # Try DrissionPage first, fall back to HTTP
    print("\n  Starting bot...")
    try:
        recorder = run_bot_with_drission()
    except ImportError:
        print("  DrissionPage not available, using HTTP mode...")
        recorder = run_bot_headless()

    session = recorder.get_session()
    print(f"\n  Recorded {len(session['events'])} events")

    # Save activity log
    log_path = os.path.join(OUTPUT_DIR, f"{session['sessionId']}_activity.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2)
    print(f"  Activity saved: {log_path}")

    # Send to detection engine
    print(f"\n  Sending to detection engine...")
    try:
        resp = requests.post(
            DETECTION_API,
            json=session,
            params={"ipAddress": "127.0.0.1"},
            timeout=10,
        )
        if resp.status_code == 200:
            result = resp.json()
            detected = result.get("detected", False)
            score = result.get("aiProbabilityScore", 0)

            print(f"\n  {'🚨 BOT DETECTED' if detected else '✓ Not detected'}")
            print(f"  Score: {score:.4f}")

            if result.get("ban"):
                ban = result["ban"]
                print(f"  Ban: {ban['banType']} ({ban['penalty']}) expires {ban.get('expiresAt', 'never')}")
                print(f"  Triggered: {ban['triggeredRule']}")

            if result.get("signals"):
                print(f"\n  Signal breakdown:")
                for s in result["signals"]:
                    bar = "█" * int(s["score"] * 20)
                    print(f"    {s['signalName']:25} {s['score']:.2f} {bar}")

            # Save detection result
            result_path = os.path.join(OUTPUT_DIR, f"{session['sessionId']}_detection.json")
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            print(f"\n  Detection result saved: {result_path}")
        else:
            print(f"  API returned {resp.status_code}: {resp.text[:200]}")
    except requests.exceptions.ConnectionError:
        print(f"  Could not connect to {DETECTION_API}")
        print(f"  Start the server first: dotnet run --urls http://localhost:5000")
        print(f"  (in AISecutity/AISecutity folder)")

    # Also run ML prediction
    print(f"\n  Running ML prediction...")
    try:
        import pickle
        model_path = "./ml/output/bot_detector_v2.pkl"
        if os.path.exists(model_path):
            import sys
            sys.path.insert(0, "./ml")
            from predict import predict_session, load_model
            model, feature_names = load_model(model_path)
            ml_result = predict_session(model, feature_names, session)
            print(f"  ML verdict: {ml_result['prediction']} (confidence: {ml_result['confidence']:.3f})")

            ml_path = os.path.join(OUTPUT_DIR, f"{session['sessionId']}_ml_prediction.json")
            with open(ml_path, "w", encoding="utf-8") as f:
                json.dump(ml_result, f, indent=2)
    except Exception as e:
        print(f"  ML prediction failed: {e}")

    print(f"\n{'=' * 70}")
    print(f"  All activity data saved to {OUTPUT_DIR}/")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
