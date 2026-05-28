"""
Generate adversarial bot data that NEVER hits /api/ endpoints.

These bots only browse normal pages (/products, /home, /blog) just like humans,
but their behavioral fingerprint (timing, mouse, keyboard) still betrays them.

This forces the ML model to learn from behavioral signals, not just endpoint patterns.

Three difficulty levels:
1. Medium bots — browse-only but still have timing/mouse tells
2. Hard bots — mimic human timing but mouse speed is slightly off
3. Extreme bots — nearly perfect human mimicry, only detectable by subtle patterns
"""

import json
import math
import os
import random
from datetime import datetime, timedelta, timezone

import numpy as np

OUTPUT_DIR = "./ml/adversarial_data"

HUMAN_ENDPOINTS = [
    "/home", "/about", "/products", "/products/1", "/products/2",
    "/products/3", "/products/5", "/products/8", "/products/12",
    "/blog", "/blog/post-1", "/blog/post-2", "/faq", "/contact",
    "/cart", "/checkout", "/account/settings", "/search?q=shoes",
]

HUMAN_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]


def generate_medium_bot(index: int, base_time: datetime) -> dict:
    """Bot that only browses normal pages but has robotic timing and mouse."""
    session_id = f"adv-medium-{index:04d}"
    events = []
    current_time = base_time + timedelta(seconds=random.uniform(0, 60))
    num_events = random.randint(10, 25)

    mouse_x, mouse_y = random.randint(300, 800), random.randint(200, 500)

    for i in range(num_events):
        # Medium bot: timing is too regular (low CV ~0.3)
        interval = random.gauss(1200, 350)
        interval = max(300, interval)

        # Occasionally adds a short pause but never a real idle gap
        if random.random() < 0.08:
            interval += random.uniform(2000, 4000)

        current_time += timedelta(milliseconds=interval)

        event_type = random.choice(["click", "scroll", "navigation", "scroll", "click"])
        endpoint = random.choice(HUMAN_ENDPOINTS)

        # Mouse: speed is too high and too consistent
        target_x = random.randint(100, 1800)
        target_y = random.randint(100, 1000)
        speed = random.uniform(900, 1300)  # Slightly above human avg (697)

        mouse = {
            "x": target_x,
            "y": target_y,
            "speed": round(speed, 1),
            "hasCurve": random.random() < 0.6,  # Some curves but not enough
        }

        keyboard = None
        if event_type == "keypress" or (random.random() < 0.1):
            event_type = "keypress"
            keyboard = {
                "interKeyDelayMs": random.gauss(90, 15),  # Faster than human avg (135)
                "burstLength": random.randint(8, 20),
                "errorRate": random.uniform(0.0, 0.02),  # Too few errors
            }

        events.append({
            "sessionId": session_id,
            "userId": f"adv-user-{random.randint(1, 100):03d}",
            "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%S.") + f"{current_time.microsecond // 1000:03d}Z",
            "eventType": event_type,
            "endpoint": endpoint,
            "durationMs": random.randint(200, 2000),
            "mouse": mouse,
            "keyboard": keyboard,
        })

    return {
        "sessionId": session_id,
        "userId": events[0]["userId"],
        "userAgent": random.choice(HUMAN_USER_AGENTS),
        "ipAddress": f"192.168.{random.randint(1, 10)}.{random.randint(1, 254)}",
        "events": events,
        "label": "bot",
        "difficulty": "medium",
    }


def generate_hard_bot(index: int, base_time: datetime) -> dict:
    """Bot with human-like timing but mouse speed/consistency still betrays it."""
    session_id = f"adv-hard-{index:04d}"
    events = []
    current_time = base_time + timedelta(seconds=random.uniform(0, 90))
    num_events = random.randint(8, 20)

    mouse_x, mouse_y = random.randint(300, 800), random.randint(200, 500)

    for i in range(num_events):
        # Human-like timing (log-normal distribution)
        interval = random.lognormvariate(7.1, 0.55)
        interval = max(500, min(interval, 20000))

        # Real pauses like humans
        if random.random() < 0.12:
            interval += random.uniform(3000, 10000)
        if random.random() < 0.05:
            interval += random.uniform(10000, 25000)

        current_time += timedelta(milliseconds=interval)

        event_type = random.choice(["click", "scroll", "navigation", "scroll", "click", "keypress"])
        endpoint = random.choice(HUMAN_ENDPOINTS)

        # Mouse: curves are present but speed is consistently high
        target_x = random.randint(100, 1800)
        target_y = random.randint(100, 1000)

        # The tell: speed clusters around 950-1100 (human avg is 697, std is high)
        speed = random.gauss(1000, 80)  # Low variance around high value
        speed = max(700, min(speed, 1200))

        mouse = {
            "x": target_x,
            "y": target_y,
            "speed": round(speed, 1),
            "hasCurve": random.random() < 0.75,  # Mostly curves
        }

        keyboard = None
        if event_type == "keypress":
            # Typing speed is slightly too fast and consistent
            keyboard = {
                "interKeyDelayMs": random.gauss(105, 20),  # Slightly fast
                "burstLength": random.randint(5, 12),
                "errorRate": random.uniform(0.01, 0.04),  # Some errors but low
            }

        events.append({
            "sessionId": session_id,
            "userId": f"adv-user-{random.randint(1, 100):03d}",
            "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%S.") + f"{current_time.microsecond // 1000:03d}Z",
            "eventType": event_type,
            "endpoint": endpoint,
            "durationMs": random.randint(500, 5000),
            "mouse": mouse,
            "keyboard": keyboard,
        })

    return {
        "sessionId": session_id,
        "userId": events[0]["userId"],
        "userAgent": random.choice(HUMAN_USER_AGENTS),
        "ipAddress": f"192.168.{random.randint(1, 10)}.{random.randint(1, 254)}",
        "events": events,
        "label": "bot",
        "difficulty": "hard",
    }


def generate_extreme_bot(index: int, base_time: datetime) -> dict:
    """Nearly undetectable bot. Only subtle statistical patterns betray it.

    Tells:
    - Mouse speed variance is slightly lower than real humans (CV 0.25 vs 0.37)
    - Never makes more than 5% typos (humans go up to 12%)
    - Session always has exactly the right number of pauses (too perfect)
    - Never revisits the same page twice in a row (humans do)
    """
    session_id = f"adv-extreme-{index:04d}"
    events = []
    current_time = base_time + timedelta(seconds=random.uniform(0, 120))
    num_events = random.randint(8, 18)

    visited_endpoints = []

    for i in range(num_events):
        # Perfect human timing
        interval = random.lognormvariate(7.2, 0.6)
        interval = max(400, min(interval, 25000))

        if random.random() < 0.15:
            interval += random.uniform(3000, 12000)
        if random.random() < 0.06:
            interval += random.uniform(10000, 20000)

        current_time += timedelta(milliseconds=interval)

        event_type = random.choice(["click", "scroll", "navigation", "scroll", "click", "keypress"])

        # Never revisits same page consecutively (subtle tell)
        available = [ep for ep in HUMAN_ENDPOINTS if ep != (visited_endpoints[-1] if visited_endpoints else "")]
        endpoint = random.choice(available)
        visited_endpoints.append(endpoint)

        # Mouse: realistic speed range but variance is slightly too low
        target_x = random.randint(100, 1800)
        target_y = random.randint(100, 1000)
        speed = random.gauss(720, 180)  # Close to human (697 avg) but CV is 0.25 vs 0.37
        speed = max(200, min(speed, 1200))

        mouse = {
            "x": target_x,
            "y": target_y,
            "speed": round(speed, 1),
            "hasCurve": random.random() < 0.85,
        }

        keyboard = None
        if event_type == "keypress":
            keyboard = {
                "interKeyDelayMs": random.gauss(138, 40),  # Very close to human
                "burstLength": random.randint(3, 8),
                "errorRate": random.uniform(0.02, 0.05),  # Errors but capped at 5%
            }

        events.append({
            "sessionId": session_id,
            "userId": f"adv-user-{random.randint(1, 100):03d}",
            "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%S.") + f"{current_time.microsecond // 1000:03d}Z",
            "eventType": event_type,
            "endpoint": endpoint,
            "durationMs": random.randint(500, 6000),
            "mouse": mouse,
            "keyboard": keyboard,
        })

    return {
        "sessionId": session_id,
        "userId": events[0]["userId"],
        "userAgent": random.choice(HUMAN_USER_AGENTS),
        "ipAddress": f"192.168.{random.randint(1, 10)}.{random.randint(1, 254)}",
        "events": events,
        "label": "bot",
        "difficulty": "extreme",
    }


def generate_real_human(index: int, base_time: datetime) -> dict:
    """Generate a realistic human session for balanced training."""
    session_id = f"adv-human-{index:04d}"
    events = []
    current_time = base_time + timedelta(seconds=random.uniform(0, 120))
    num_events = random.randint(5, 20)

    last_endpoint = ""

    for i in range(num_events):
        # Real human timing: highly variable
        if random.random() < 0.15:
            interval = random.uniform(3000, 15000)
        elif random.random() < 0.08:
            interval = random.uniform(10000, 30000)
        else:
            interval = random.lognormvariate(7.3, 0.7)
            interval = max(300, min(interval, 30000))

        current_time += timedelta(milliseconds=interval)

        event_type = random.choice(["click", "scroll", "keypress", "navigation", "scroll", "click"])

        # Humans DO revisit pages (back button, re-reading)
        if random.random() < 0.15 and last_endpoint:
            endpoint = last_endpoint  # Go back to same page
        else:
            endpoint = random.choice(HUMAN_ENDPOINTS)
        last_endpoint = endpoint

        # Human mouse: wide speed range, high variance
        speed = random.gauss(700, 260)  # High std = high CV
        speed = max(150, min(speed, 1400))

        mouse = None
        if event_type in ("click", "scroll", "navigation"):
            mouse = {
                "x": random.randint(100, 1800),
                "y": random.randint(100, 1000),
                "speed": round(speed, 1),
                "hasCurve": random.random() < 0.88,
            }

        keyboard = None
        if event_type == "keypress":
            keyboard = {
                "interKeyDelayMs": random.gauss(145, 55),  # High variance
                "burstLength": random.randint(2, 7),
                "errorRate": random.uniform(0.03, 0.12),  # Real error rates
            }

        events.append({
            "sessionId": session_id,
            "userId": f"adv-user-{random.randint(100, 300):03d}",
            "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%S.") + f"{current_time.microsecond // 1000:03d}Z",
            "eventType": event_type,
            "endpoint": endpoint,
            "durationMs": random.randint(500, 8000),
            "mouse": mouse,
            "keyboard": keyboard,
        })

    return {
        "sessionId": session_id,
        "userId": events[0]["userId"],
        "userAgent": random.choice(HUMAN_USER_AGENTS),
        "ipAddress": f"192.168.{random.randint(1, 10)}.{random.randint(1, 254)}",
        "events": events,
        "label": "human",
        "difficulty": "real",
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    base_time = datetime(2026, 5, 28, 16, 0, 0, tzinfo=timezone.utc)

    print("=" * 70)
    print("  ADVERSARIAL DATA GENERATOR")
    print("  Bots that NEVER hit /api/ — forces ML to learn behavior")
    print("=" * 70)

    sessions = []

    # 200 medium bots
    print("\n  Generating 200 medium bots...")
    for i in range(200):
        sessions.append(generate_medium_bot(i, base_time))

    # 200 hard bots
    print("  Generating 200 hard bots...")
    for i in range(200):
        sessions.append(generate_hard_bot(i, base_time))

    # 200 extreme bots
    print("  Generating 200 extreme bots...")
    for i in range(200):
        sessions.append(generate_extreme_bot(i, base_time))

    # 600 humans (balanced)
    print("  Generating 600 humans...")
    for i in range(600):
        sessions.append(generate_real_human(i, base_time))

    random.shuffle(sessions)

    # Save
    all_path = os.path.join(OUTPUT_DIR, "adversarial_sessions.json")
    with open(all_path, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)

    # Summary
    bots = [s for s in sessions if s["label"] == "bot"]
    humans = [s for s in sessions if s["label"] == "human"]

    summary = {
        "total_sessions": len(sessions),
        "bots": len(bots),
        "humans": len(humans),
        "bot_breakdown": {
            "medium": sum(1 for s in bots if s["difficulty"] == "medium"),
            "hard": sum(1 for s in bots if s["difficulty"] == "hard"),
            "extreme": sum(1 for s in bots if s["difficulty"] == "extreme"),
        },
        "key_constraint": "NO bot hits /api/ endpoints — all browse normal pages only",
        "detection_challenge": "Model must learn from timing, mouse, keyboard patterns alone",
    }

    with open(os.path.join(OUTPUT_DIR, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n  Generated {len(sessions)} sessions:")
    print(f"    Medium bots:  200 (timing + mouse tells)")
    print(f"    Hard bots:    200 (only mouse speed consistency)")
    print(f"    Extreme bots: 200 (nearly undetectable)")
    print(f"    Humans:       600")
    print(f"\n  Saved to {all_path}")
    print(f"  NO bot hits /api/ endpoints — pure behavioral detection required")
    print("=" * 70)


if __name__ == "__main__":
    main()
