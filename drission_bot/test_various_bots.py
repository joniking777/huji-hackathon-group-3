"""
Test the bot identifier against 5 different types of bots.

Each bot simulates a different real-world attack pattern:
1. Speed Scraper — blasts through pages as fast as possible
2. Stealth Crawler — mimics human timing but targets data endpoints
3. Form Spammer — fills and submits forms rapidly (brute force)
4. Content Thief — scrolls and copies content systematically
5. DrissionPage Bot — real browser automation (our bot)

Runs each against the detection engine and reports which get caught.
"""

import json
import os
import random
import time
from datetime import datetime, timedelta, timezone

import requests

API_URL = "http://localhost:5000/api/ban/analyze-and-ban"
OUTPUT_DIR = "./drission_bot/test_results"


def make_timestamp(base: datetime, offset_ms: float) -> str:
    t = base + timedelta(milliseconds=offset_ms)
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}Z"


def bot_1_speed_scraper() -> dict:
    """Speed Scraper: Hits pages every 50-150ms, no mouse, no keyboard.
    Like a requests/scrapy bot hammering endpoints."""
    base = datetime(2026, 5, 28, 18, 0, 0, tzinfo=timezone.utc)
    events = []
    offset = 0

    pages = ["/products", "/products/1", "/products/2", "/products/3",
             "/products/4", "/products/5", "/api/products", "/api/prices",
             "/api/inventory", "/api/search?q=all", "/products/6",
             "/products/7", "/api/products/1/reviews", "/api/cart/add",
             "/checkout", "/api/checkout"]

    for i, page in enumerate(pages):
        offset += random.uniform(50, 150)  # Superhuman speed
        events.append({
            "sessionId": "speed-scraper-001",
            "userId": "scraper-bot",
            "timestamp": make_timestamp(base, offset),
            "eventType": "api_call" if "/api/" in page else "navigation",
            "endpoint": page,
            "durationMs": random.randint(10, 40),
            "mouse": None,
            "keyboard": None,
        })

    return {
        "sessionId": "speed-scraper-001",
        "userId": "scraper-bot",
        "userAgent": "python-requests/2.31.0",
        "ipAddress": "10.0.1.100",
        "events": events,
    }


def bot_2_stealth_crawler() -> dict:
    """Stealth Crawler: Human-like timing, curves mouse, but systematically
    visits every product page in order. Never revisits, never scrolls."""
    base = datetime(2026, 5, 28, 18, 5, 0, tzinfo=timezone.utc)
    events = []
    offset = 0

    # Systematic: visits products 1-15 in order
    pages = ["/home"] + [f"/products/{i}" for i in range(1, 16)]

    for i, page in enumerate(pages):
        offset += random.lognormvariate(7.2, 0.5)  # Human-like timing
        offset = max(offset, (i + 1) * 800)

        events.append({
            "sessionId": "stealth-crawler-001",
            "userId": "crawler-user",
            "timestamp": make_timestamp(base, offset),
            "eventType": "navigation",
            "endpoint": page,
            "durationMs": random.randint(800, 3000),
            "mouse": {
                "x": random.randint(200, 1600),
                "y": random.randint(150, 900),
                "speed": random.gauss(750, 100),  # Slightly too consistent
                "hasCurve": True,
            },
            "keyboard": None,
        })

    return {
        "sessionId": "stealth-crawler-001",
        "userId": "crawler-user",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        "ipAddress": "192.168.5.42",
        "events": events,
    }


def bot_3_form_spammer() -> dict:
    """Form Spammer: Rapidly fills forms with perfect typing, submits repeatedly.
    Simulates credential stuffing or spam bot."""
    base = datetime(2026, 5, 28, 18, 10, 0, tzinfo=timezone.utc)
    events = []
    offset = 0

    for attempt in range(12):
        # Navigate to login
        offset += random.uniform(300, 800)
        events.append({
            "sessionId": "form-spammer-001",
            "userId": "spammer-bot",
            "timestamp": make_timestamp(base, offset),
            "eventType": "navigation",
            "endpoint": "/login",
            "durationMs": random.randint(100, 300),
            "mouse": {
                "x": random.randint(400, 600),
                "y": random.randint(300, 400),
                "speed": random.uniform(3000, 6000),  # Superhuman mouse speed
                "hasCurve": False,
            },
            "keyboard": None,
        })

        # Type username (perfect, fast)
        offset += random.uniform(100, 300)
        events.append({
            "sessionId": "form-spammer-001",
            "userId": "spammer-bot",
            "timestamp": make_timestamp(base, offset),
            "eventType": "keypress",
            "endpoint": "/login",
            "durationMs": random.randint(200, 400),
            "mouse": None,
            "keyboard": {
                "interKeyDelayMs": random.uniform(15, 25),  # Impossibly fast
                "burstLength": random.randint(20, 40),
                "errorRate": 0.0,  # Perfect typing
            },
        })

        # Type password
        offset += random.uniform(50, 150)
        events.append({
            "sessionId": "form-spammer-001",
            "userId": "spammer-bot",
            "timestamp": make_timestamp(base, offset),
            "eventType": "keypress",
            "endpoint": "/login",
            "durationMs": random.randint(150, 300),
            "mouse": None,
            "keyboard": {
                "interKeyDelayMs": random.uniform(12, 20),
                "burstLength": random.randint(15, 30),
                "errorRate": 0.0,
            },
        })

        # Submit
        offset += random.uniform(50, 100)
        events.append({
            "sessionId": "form-spammer-001",
            "userId": "spammer-bot",
            "timestamp": make_timestamp(base, offset),
            "eventType": "form_submit",
            "endpoint": "/api/auth/login",
            "durationMs": random.randint(20, 50),
            "mouse": {
                "x": 500,
                "y": 450,
                "speed": 5000,
                "hasCurve": False,
            },
            "keyboard": None,
        })

    return {
        "sessionId": "form-spammer-001",
        "userId": "spammer-bot",
        "userAgent": "Mozilla/5.0 (compatible; Bot/1.0)",
        "ipAddress": "10.0.2.200",
        "events": events,
    }


def bot_4_content_thief() -> dict:
    """Content Thief: Scrolls through pages systematically, selecting text.
    Mimics a bot that copies article content. Moderate speed, no keyboard."""
    base = datetime(2026, 5, 28, 18, 15, 0, tzinfo=timezone.utc)
    events = []
    offset = 0

    articles = ["/blog/post-1", "/blog/post-2", "/blog/post-3",
                "/blog/post-4", "/blog/post-5", "/blog/post-6"]

    for article in articles:
        # Navigate to article
        offset += random.uniform(1000, 2000)
        events.append({
            "sessionId": "content-thief-001",
            "userId": "thief-bot",
            "timestamp": make_timestamp(base, offset),
            "eventType": "navigation",
            "endpoint": article,
            "durationMs": random.randint(500, 1500),
            "mouse": {
                "x": random.randint(300, 800),
                "y": random.randint(100, 300),
                "speed": random.uniform(600, 900),
                "hasCurve": random.random() < 0.5,
            },
            "keyboard": None,
        })

        # Systematic scrolling (3-5 scrolls per page, evenly spaced)
        for scroll_i in range(random.randint(3, 5)):
            offset += random.uniform(800, 1200)  # Too regular
            events.append({
                "sessionId": "content-thief-001",
                "userId": "thief-bot",
                "timestamp": make_timestamp(base, offset),
                "eventType": "scroll",
                "endpoint": article,
                "durationMs": random.randint(300, 600),
                "mouse": {
                    "x": random.randint(400, 700),
                    "y": 200 + scroll_i * 200,  # Linear scroll pattern
                    "speed": random.uniform(400, 600),
                    "hasCurve": False,
                },
                "keyboard": None,
            })

        # Select all text (triple click pattern)
        offset += random.uniform(200, 400)
        events.append({
            "sessionId": "content-thief-001",
            "userId": "thief-bot",
            "timestamp": make_timestamp(base, offset),
            "eventType": "click",
            "endpoint": article,
            "durationMs": 50,
            "mouse": {"x": 400, "y": 500, "speed": 2000, "hasCurve": False},
            "keyboard": None,
        })

    return {
        "sessionId": "content-thief-001",
        "userId": "thief-bot",
        "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
        "ipAddress": "172.16.0.55",
        "events": events,
    }


def bot_5_drission_bot() -> dict:
    """DrissionPage Bot: Real browser automation patterns.
    Consistent timing (~6s per page due to page load), high mouse speed,
    no curves, no keyboard interaction."""
    base = datetime(2026, 5, 28, 18, 20, 0, tzinfo=timezone.utc)
    events = []
    offset = 0

    pages = ["/home", "/about", "/products", "/contact", "/products",
             "/home", "/home", "/about", "/contact", "/products"]

    for page in pages:
        offset += random.gauss(6800, 200)  # Very consistent ~6.8s (page load)
        events.append({
            "sessionId": "drission-bot-001",
            "userId": "drission-user",
            "timestamp": make_timestamp(base, offset),
            "eventType": "navigation",
            "endpoint": page,
            "durationMs": random.randint(5800, 6200),
            "mouse": {
                "x": random.randint(100, 1200),
                "y": random.randint(100, 800),
                "speed": random.uniform(800, 1500),  # High speed
                "hasCurve": random.random() < 0.3,  # Rarely curves
            },
            "keyboard": None,
        })

    return {
        "sessionId": "drission-bot-001",
        "userId": "drission-user",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        "ipAddress": "127.0.0.1",
        "events": events,
    }


def bot_6_camoufox() -> dict:
    """Camoufox Bot: Hardened Firefox fork designed to evade detection.

    Camoufox patches browser fingerprinting but still has automation tells:
    - Mouse movements use Bezier curves but with mathematical precision
      (jerk profile is too smooth — no hand tremor)
    - Timing is randomized but from a uniform distribution (not log-normal like humans)
    - Mouse positions land exactly on elements (pixel-perfect targeting)
    - Speed between points is calculated, not physical (constant acceleration)
    """
    base = datetime(2026, 5, 28, 18, 25, 0, tzinfo=timezone.utc)
    events = []
    offset = 0

    pages = ["/home", "/products", "/products/3", "/products/7",
             "/cart", "/checkout", "/products/12", "/about",
             "/products/3", "/home", "/blog"]

    # Camoufox uses randomized delays but from uniform distribution
    for i, page in enumerate(pages):
        offset += random.uniform(1500, 4500)  # Uniform, not log-normal

        # Mouse: Bezier-calculated positions — looks curved but jerk is wrong
        # Points are mathematically spaced (constant velocity segments)
        prev_x = events[-1]["mouse"]["x"] if events and events[-1].get("mouse") else 600
        prev_y = events[-1]["mouse"]["y"] if events and events[-1].get("mouse") else 400

        # Camoufox calculates target position precisely (center of element)
        target_x = 400 + (i * 97) % 800  # Deterministic-looking positions
        target_y = 250 + (i * 73) % 500

        # Speed is calculated from distance/time — too consistent per-move
        distance = ((target_x - prev_x)**2 + (target_y - prev_y)**2)**0.5
        move_time = random.uniform(300, 500)  # Fixed move duration
        speed = distance / (move_time / 1000)

        events.append({
            "sessionId": "camoufox-bot-001",
            "userId": "camoufox-user",
            "timestamp": make_timestamp(base, offset),
            "eventType": random.choice(["click", "navigation"]),
            "endpoint": page,
            "durationMs": random.randint(800, 2500),
            "mouse": {
                "x": target_x,
                "y": target_y,
                "speed": round(speed, 1),
                "hasCurve": True,  # Camoufox always curves (Bezier)
            },
            "keyboard": None,
        })

        # Camoufox sometimes scrolls (with calculated positions)
        if random.random() < 0.4:
            offset += random.uniform(500, 1500)
            events.append({
                "sessionId": "camoufox-bot-001",
                "userId": "camoufox-user",
                "timestamp": make_timestamp(base, offset),
                "eventType": "scroll",
                "endpoint": page,
                "durationMs": random.randint(300, 800),
                "mouse": {
                    "x": target_x,  # Same X (scrolling doesn't move X)
                    "y": target_y + random.randint(100, 300),
                    "speed": round(random.uniform(400, 700), 1),
                    "hasCurve": True,
                },
                "keyboard": None,
            })

    return {
        "sessionId": "camoufox-bot-001",
        "userId": "camoufox-user",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "ipAddress": "203.0.113.42",
        "events": events,
    }


def generate_human_control() -> dict:
    """Control: A real human session for comparison."""
    base = datetime(2026, 5, 28, 18, 25, 0, tzinfo=timezone.utc)
    events = []
    offset = 0

    pages = ["/home", "/products", "/products", "/products/3",
             "/products/3", "/cart", "/home", "/blog/post-1"]

    for page in pages:
        # Highly variable timing
        if random.random() < 0.2:
            offset += random.uniform(5000, 15000)  # Thinking
        else:
            offset += random.lognormvariate(7.5, 0.8)

        events.append({
            "sessionId": "human-control-001",
            "userId": "real-human",
            "timestamp": make_timestamp(base, offset),
            "eventType": random.choice(["click", "navigation", "scroll"]),
            "endpoint": page,
            "durationMs": random.randint(1000, 5000),
            "mouse": {
                "x": random.randint(100, 1800),
                "y": random.randint(100, 1000),
                "speed": random.gauss(650, 250),  # Wide variance
                "hasCurve": random.random() < 0.9,
            },
            "keyboard": None,
        })

        # Human scrolls and clicks randomly
        if random.random() < 0.4:
            offset += random.uniform(1000, 4000)
            events.append({
                "sessionId": "human-control-001",
                "userId": "real-human",
                "timestamp": make_timestamp(base, offset),
                "eventType": "scroll",
                "endpoint": page,
                "durationMs": random.randint(1000, 3000),
                "mouse": {
                    "x": random.randint(300, 1500),
                    "y": random.randint(200, 900),
                    "speed": random.gauss(500, 200),
                    "hasCurve": True,
                },
                "keyboard": None,
            })

        if random.random() < 0.2:
            offset += random.uniform(2000, 8000)
            events.append({
                "sessionId": "human-control-001",
                "userId": "real-human",
                "timestamp": make_timestamp(base, offset),
                "eventType": "keypress",
                "endpoint": page,
                "durationMs": random.randint(3000, 8000),
                "mouse": None,
                "keyboard": {
                    "interKeyDelayMs": random.gauss(150, 50),
                    "burstLength": random.randint(2, 6),
                    "errorRate": random.uniform(0.04, 0.12),
                },
            })

    return {
        "sessionId": "human-control-001",
        "userId": "real-human",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        "ipAddress": "192.168.1.50",
        "events": events,
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 70)
    print("  BOT IDENTIFIER TEST — 5 Different Bot Types + Human Control")
    print("=" * 70)

    bots = [
        ("1. Speed Scraper", bot_1_speed_scraper(), "Hammers pages every 50-150ms, hits /api/ endpoints"),
        ("2. Stealth Crawler", bot_2_stealth_crawler(), "Human timing but visits pages systematically in order"),
        ("3. Form Spammer", bot_3_form_spammer(), "Rapid form fills with perfect typing, credential stuffing"),
        ("4. Content Thief", bot_4_content_thief(), "Scrolls articles systematically, copies content"),
        ("5. DrissionPage Bot", bot_5_drission_bot(), "Real browser automation, consistent page load timing"),
        ("6. Camoufox Bot", bot_6_camoufox(), "Hardened Firefox fork, Bezier curves but wrong jerk profile"),
        ("7. Human (control)", generate_human_control(), "Real human browsing pattern for comparison"),
    ]

    results = []

    for name, session, description in bots:
        print(f"\n  {'─' * 60}")
        print(f"  {name}")
        print(f"  {description}")
        print(f"  Events: {len(session['events'])}, UA: {session['userAgent'][:50]}...")

        try:
            resp = requests.post(
                API_URL,
                json=session,
                params={"ipAddress": session["ipAddress"]},
                timeout=10,
            )

            if resp.status_code == 200:
                result = resp.json()
                detected = result.get("detected", False)
                score = result.get("aiProbabilityScore", 0)

                status = "🚨 DETECTED" if detected else "✅ PASSED"
                print(f"  Result: {status} (score: {score:.4f})")

                if result.get("ban"):
                    ban = result["ban"]
                    print(f"  Ban: {ban['banType']} / {ban['penalty']}")
                    print(f"  Rule: {ban['triggeredRule']}")

                # Show top signals
                signals = result.get("signals", [])
                top_signals = sorted(signals, key=lambda s: s["score"], reverse=True)[:3]
                for s in top_signals:
                    bar = "█" * int(s["score"] * 15)
                    print(f"    {s['signalName']:22} {s['score']:.2f} {bar}")

                results.append({
                    "name": name,
                    "description": description,
                    "detected": detected,
                    "score": score,
                    "signals": signals,
                    "ban": result.get("ban"),
                })
            else:
                print(f"  ERROR: {resp.status_code}")
                results.append({"name": name, "detected": None, "error": resp.status_code})

        except requests.exceptions.ConnectionError:
            print(f"  ERROR: Cannot connect to {API_URL}")
            print(f"  Start server: dotnet run --urls http://localhost:5000")
            return

    # Summary table
    print(f"\n\n  {'═' * 60}")
    print(f"  SUMMARY — Bot Identifier Test Results")
    print(f"  {'═' * 60}")
    print(f"\n  {'Bot Type':<25} {'Score':>7} {'Detected':>10} {'Verdict'}")
    print(f"  {'─' * 60}")

    for r in results:
        if r.get("detected") is None:
            continue
        score = r["score"]
        detected = r["detected"]
        verdict = "🚨 BANNED" if detected else "✅ CLEAN"
        print(f"  {r['name']:<25} {score:>7.4f} {'YES' if detected else 'NO':>10} {verdict}")

    # Stats
    bot_results = [r for r in results if r.get("detected") is not None and "Human" not in r["name"]]
    caught = sum(1 for r in bot_results if r["detected"])
    total = len(bot_results)
    human_result = next((r for r in results if "Human" in r.get("name", "")), None)

    print(f"\n  {'─' * 60}")
    print(f"  Bots caught: {caught}/{total} ({caught/total*100:.0f}%)")
    if human_result:
        print(f"  Human false alarm: {'YES ⚠️' if human_result.get('detected') else 'NO ✓'}")
    print(f"  {'═' * 60}")

    # Save
    output_path = os.path.join(OUTPUT_DIR, "various_bots_test.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Full results saved to {output_path}")


if __name__ == "__main__":
    main()
