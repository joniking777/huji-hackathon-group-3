"""
Generate realistic bot activity session data for the AISecutity detection engine.

Produces JSON files matching the ActivitySession/ActivityEvent schema that the
C# detection engine consumes. Generates both bot sessions (detectable patterns)
and human sessions (natural patterns) for training/testing.

Output: ./bot_activity_sessions/
"""

import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

OUTPUT_DIR = "./bot_activity_sessions"

# Bot user agents (known AI crawlers + generic bots)
BOT_USER_AGENTS = [
    "Mozilla/5.0 (compatible; GPTBot/1.0; +https://openai.com/gptbot)",
    "Mozilla/5.0 (compatible; ClaudeBot/1.0; +https://anthropic.com)",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "python-requests/2.31.0",
    "aiohttp/3.9.5",
    "Scrapy/2.11.0",
    "curl/8.4.0",
    "Go-http-client/2.0",
    "Java/17.0.1",
]

# Human user agents
HUMAN_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
    "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/125.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

# Endpoints that bots typically target
BOT_ENDPOINTS = [
    "/api/products", "/api/products/1", "/api/products/2", "/api/products/3",
    "/api/products/1/reviews", "/api/products/2/reviews",
    "/api/cart/add", "/api/cart/checkout", "/api/users/profile",
    "/api/search?q=deals", "/api/inventory", "/api/prices",
]

# Endpoints humans browse
HUMAN_ENDPOINTS = [
    "/home", "/about", "/products", "/products/5", "/products/12",
    "/products/5/review", "/cart", "/checkout", "/contact",
    "/blog", "/blog/post-1", "/faq", "/account/settings",
]

HUMAN_EVENT_TYPES = ["click", "scroll", "keypress", "navigation", "form_submit"]
BOT_EVENT_TYPES = ["navigation", "api_call", "api_call", "api_call", "form_submit"]


def generate_bot_session(session_index: int, base_time: datetime) -> dict:
    """Generate a single bot session with detectable AI patterns."""
    session_id = f"bot-sess-{session_index:04d}"
    user_id = f"bot-user-{random.randint(1, 50):03d}"

    # Bot characteristics
    num_events = random.randint(8, 30)
    base_interval_ms = random.uniform(50, 200)  # Very fast, consistent intervals
    interval_jitter = random.uniform(0.02, 0.12)  # Low jitter = regular timing

    events = []
    current_time = base_time + timedelta(seconds=random.uniform(0, 60))

    for i in range(num_events):
        # Consistent timing with very low variation
        interval = base_interval_ms * (1 + random.gauss(0, interval_jitter))
        interval = max(10, interval)  # Never negative
        current_time += timedelta(milliseconds=interval)

        event_type = random.choice(BOT_EVENT_TYPES)
        endpoint = random.choice(BOT_ENDPOINTS)

        # Bot mouse: straight lines, high speed, no curves
        mouse = None
        if random.random() < 0.6:  # Bots sometimes have mouse data
            prev_x = events[-1]["mouse"]["x"] if events and events[-1].get("mouse") else random.randint(0, 1920)
            prev_y = events[-1]["mouse"]["y"] if events and events[-1].get("mouse") else random.randint(0, 1080)
            # Move in straight line with constant speed
            mouse = {
                "x": prev_x + random.randint(50, 300),
                "y": prev_y + random.randint(-5, 5),  # Nearly horizontal = linear
                "speed": random.uniform(5000, 15000),  # Superhuman speed
                "hasCurve": False,
            }

        # Bot keyboard: perfect typing, zero errors
        keyboard = None
        if event_type in ("form_submit", "keypress") or (event_type == "api_call" and random.random() < 0.2):
            keyboard = {
                "interKeyDelayMs": random.uniform(8, 20),  # Impossibly fast and consistent
                "burstLength": random.randint(30, 100),  # Long bursts without pause
                "errorRate": 0.0,  # Perfect typing
            }

        events.append({
            "sessionId": session_id,
            "userId": user_id,
            "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%S.") + f"{current_time.microsecond // 1000:03d}Z",
            "eventType": event_type,
            "endpoint": endpoint,
            "durationMs": random.randint(10, 60),  # Very fast actions
            "mouse": mouse,
            "keyboard": keyboard,
        })

    return {
        "sessionId": session_id,
        "userId": user_id,
        "userAgent": random.choice(BOT_USER_AGENTS),
        "ipAddress": f"10.0.{random.randint(0, 255)}.{random.randint(1, 254)}",
        "events": events,
        "label": "bot",  # Ground truth for training
    }


def generate_human_session(session_index: int, base_time: datetime) -> dict:
    """Generate a single human session with natural behavioral patterns."""
    session_id = f"human-sess-{session_index:04d}"
    user_id = f"human-user-{random.randint(1, 200):03d}"

    num_events = random.randint(5, 20)
    events = []
    current_time = base_time + timedelta(seconds=random.uniform(0, 120))

    for i in range(num_events):
        # Human timing: highly variable, with pauses and bursts
        if random.random() < 0.15:
            # Thinking pause (3-15 seconds)
            interval = random.uniform(3000, 15000)
        elif random.random() < 0.1:
            # Distraction (10-30 seconds)
            interval = random.uniform(10000, 30000)
        else:
            # Normal human reaction time (800-4000ms)
            interval = random.gauss(2000, 800)
            interval = max(300, interval)

        current_time += timedelta(milliseconds=interval)

        event_type = random.choice(HUMAN_EVENT_TYPES)
        endpoint = random.choice(HUMAN_ENDPOINTS)

        # Human mouse: curved movements, moderate speed
        mouse = None
        if event_type in ("click", "scroll", "navigation"):
            mouse = {
                "x": random.randint(100, 1800),
                "y": random.randint(100, 1000),
                "speed": random.uniform(200, 1200),  # Normal human speed
                "hasCurve": random.random() < 0.85,  # Humans usually curve
            }

        # Human keyboard: variable speed, makes typos
        keyboard = None
        if event_type in ("keypress", "form_submit"):
            keyboard = {
                "interKeyDelayMs": random.gauss(140, 50),  # Variable typing speed
                "burstLength": random.randint(2, 8),  # Short bursts
                "errorRate": random.uniform(0.03, 0.12),  # Humans make mistakes
            }

        events.append({
            "sessionId": session_id,
            "userId": user_id,
            "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%S.") + f"{current_time.microsecond // 1000:03d}Z",
            "eventType": event_type,
            "endpoint": endpoint,
            "durationMs": random.randint(500, 8000),  # Humans take time
            "mouse": mouse,
            "keyboard": keyboard,
        })

    return {
        "sessionId": session_id,
        "userId": user_id,
        "userAgent": random.choice(HUMAN_USER_AGENTS),
        "ipAddress": f"192.168.{random.randint(1, 10)}.{random.randint(1, 254)}",
        "events": events,
        "label": "human",  # Ground truth for training
    }


def generate_sneaky_bot_session(session_index: int, base_time: datetime) -> dict:
    """Generate a sophisticated bot that tries to mimic human behavior but still has tells."""
    session_id = f"sneaky-bot-sess-{session_index:04d}"
    user_id = f"sneaky-bot-{random.randint(1, 30):03d}"

    num_events = random.randint(8, 18)
    events = []
    current_time = base_time + timedelta(seconds=random.uniform(0, 90))

    for i in range(num_events):
        # Tries to add variation but still too regular
        interval = random.gauss(1500, 300)  # Attempts human-like but CV is still low
        interval = max(200, interval)

        # Occasionally adds a fake "pause" but it's too short
        if random.random() < 0.08:
            interval += random.uniform(1000, 2500)

        current_time += timedelta(milliseconds=interval)

        event_type = random.choice(["click", "navigation", "api_call", "scroll"])
        endpoint = random.choice(BOT_ENDPOINTS + HUMAN_ENDPOINTS[:4])

        # Tries to curve mouse but fails — speed is still too high
        mouse = None
        if random.random() < 0.7:
            mouse = {
                "x": random.randint(100, 1800),
                "y": random.randint(100, 1000),
                "speed": random.uniform(2000, 5000),  # Still faster than human
                "hasCurve": random.random() < 0.4,  # Sometimes curves, but not enough
            }

        # Tries to add typos but error rate is still suspiciously low
        keyboard = None
        if event_type in ("keypress", "form_submit"):
            keyboard = {
                "interKeyDelayMs": random.gauss(80, 15),  # Faster than human, low variance
                "burstLength": random.randint(10, 25),
                "errorRate": random.uniform(0.0, 0.02),  # Almost no errors
            }

        events.append({
            "sessionId": session_id,
            "userId": user_id,
            "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%S.") + f"{current_time.microsecond // 1000:03d}Z",
            "eventType": event_type,
            "endpoint": endpoint,
            "durationMs": random.randint(100, 1500),
            "mouse": mouse,
            "keyboard": keyboard,
        })

    return {
        "sessionId": session_id,
        "userId": user_id,
        "userAgent": random.choice(HUMAN_USER_AGENTS),  # Disguises as human browser
        "ipAddress": f"172.16.{random.randint(0, 255)}.{random.randint(1, 254)}",
        "events": events,
        "label": "sneaky_bot",  # Ground truth
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    base_time = datetime(2026, 5, 28, 10, 0, 0, tzinfo=timezone.utc)

    all_sessions = []

    # Generate 400 obvious bot sessions
    print("Generating 400 bot sessions...")
    for i in range(400):
        session = generate_bot_session(i, base_time)
        all_sessions.append(session)

    # Generate 400 human sessions
    print("Generating 400 human sessions...")
    for i in range(400):
        session = generate_human_session(i, base_time)
        all_sessions.append(session)

    # Generate 200 sneaky bot sessions (harder to detect)
    print("Generating 200 sneaky bot sessions...")
    for i in range(200):
        session = generate_sneaky_bot_session(i, base_time)
        all_sessions.append(session)

    # Shuffle so they're mixed
    random.shuffle(all_sessions)

    # Write all sessions as one big file (for bulk analysis)
    all_path = os.path.join(OUTPUT_DIR, "all_sessions.json")
    with open(all_path, "w", encoding="utf-8") as f:
        json.dump(all_sessions, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(all_sessions)} sessions to {all_path}")

    # Write separate files by type for easier testing
    bots = [s for s in all_sessions if s["label"] == "bot"]
    humans = [s for s in all_sessions if s["label"] == "human"]
    sneaky = [s for s in all_sessions if s["label"] == "sneaky_bot"]

    with open(os.path.join(OUTPUT_DIR, "bot_sessions.json"), "w", encoding="utf-8") as f:
        json.dump(bots, f, ensure_ascii=False, indent=2)

    with open(os.path.join(OUTPUT_DIR, "human_sessions.json"), "w", encoding="utf-8") as f:
        json.dump(humans, f, ensure_ascii=False, indent=2)

    with open(os.path.join(OUTPUT_DIR, "sneaky_bot_sessions.json"), "w", encoding="utf-8") as f:
        json.dump(sneaky, f, ensure_ascii=False, indent=2)

    # Write a summary
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_sessions": len(all_sessions),
        "bot_sessions": len(bots),
        "human_sessions": len(humans),
        "sneaky_bot_sessions": len(sneaky),
        "total_events": sum(len(s["events"]) for s in all_sessions),
        "avg_events_per_session": {
            "bot": sum(len(s["events"]) for s in bots) / len(bots),
            "human": sum(len(s["events"]) for s in humans) / len(humans),
            "sneaky_bot": sum(len(s["events"]) for s in sneaky) / len(sneaky),
        },
        "schema_version": "1.0",
        "compatible_with": "AISecutity.Models.ActivitySession",
    }

    with open(os.path.join(OUTPUT_DIR, "generation_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\nDone! Generated:")
    print(f"  {len(bots)} obvious bot sessions")
    print(f"  {len(humans)} human sessions")
    print(f"  {len(sneaky)} sneaky bot sessions")
    print(f"  {sum(len(s['events']) for s in all_sessions)} total events")
    print(f"\nFiles in {OUTPUT_DIR}/:")
    print(f"  all_sessions.json       - all 1000 sessions mixed")
    print(f"  bot_sessions.json       - 400 obvious bots")
    print(f"  human_sessions.json     - 400 humans")
    print(f"  sneaky_bot_sessions.json - 200 sophisticated bots")
    print(f"  generation_summary.json - metadata")


if __name__ == "__main__":
    main()
