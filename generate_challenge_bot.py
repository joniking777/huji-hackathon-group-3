"""
Generate a "challenge bot" — an advanced bot that's extremely hard to detect.

This bot uses sophisticated evasion techniques:
1. Mimics human timing distributions (adds realistic variance + pauses)
2. Simulates natural mouse curves with acceleration/deceleration
3. Types with human-like rhythm including typos and corrections
4. Browses naturally before targeting endpoints
5. Takes breaks, scrolls, hesitates like a real person

Then sends it to the detection engine to see if it gets caught.
Collects all data about the bot's behavior and the detection result.

Output: ./challenge_bot_data/
"""

import json
import math
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

import requests

OUTPUT_DIR = "./challenge_bot_data"
API_URL = "http://localhost:5000/api/detection/analyze"


def human_like_delay():
    """Generate a delay that matches human reaction time distribution.
    Uses a log-normal distribution which closely models human response times.
    """
    # Log-normal with mean ~1.5s, heavy right tail (occasional long pauses)
    delay = random.lognormvariate(7.2, 0.6)  # in ms, centered around 1300ms
    delay = max(400, min(delay, 25000))  # clamp between 400ms and 25s
    return delay


def generate_curved_mouse_path(start_x, start_y, end_x, end_y, num_points=5):
    """Generate a Bezier-curved mouse path between two points.
    Humans don't move in straight lines — they overshoot, correct, and curve.
    """
    # Add control points with random offset for natural curve
    mid_x = (start_x + end_x) / 2 + random.gauss(0, 50)
    mid_y = (start_y + end_y) / 2 + random.gauss(0, 40)

    points = []
    for t_i in range(num_points):
        t = t_i / (num_points - 1)
        # Quadratic Bezier
        x = (1 - t) ** 2 * start_x + 2 * (1 - t) * t * mid_x + t ** 2 * end_x
        y = (1 - t) ** 2 * start_y + 2 * (1 - t) * t * mid_y + t ** 2 * end_y
        # Add micro-jitter (hand tremor)
        x += random.gauss(0, 2)
        y += random.gauss(0, 2)
        points.append((int(x), int(y)))

    return points


def human_typing_pattern(text_length):
    """Generate realistic typing metrics.
    Humans type in bursts, pause to think, make errors, and correct them.
    """
    # Average typing speed varies per person (120-250ms between keys)
    base_delay = random.gauss(135, 35)
    base_delay = max(70, base_delay)

    # Burst length: humans type 3-7 chars then micro-pause
    burst = random.randint(3, 7)

    # Error rate: 2-8% for most people, higher when tired
    error_rate = random.betavariate(2, 30)  # skewed toward low but never zero
    error_rate = max(0.02, min(error_rate, 0.15))

    return {
        "interKeyDelayMs": round(base_delay, 1),
        "burstLength": burst,
        "errorRate": round(error_rate, 4),
    }


def generate_challenge_bot_session(session_index: int, base_time: datetime) -> dict:
    """Generate a single challenge bot session that's designed to evade detection.

    Strategy: Act like a real person browsing a website.
    - Start on homepage, browse around
    - Read content (scroll events with realistic timing)
    - Occasionally search or click products
    - Eventually do the "bot task" (scrape data) but disguised as normal browsing
    - Include natural pauses, backtracking, and idle moments
    """
    session_id = f"challenge-bot-{session_index:04d}"
    user_id = f"cbot-user-{random.randint(1, 100):03d}"

    events = []
    current_time = base_time + timedelta(seconds=random.uniform(0, 120))

    # Current mouse position
    mouse_x = random.randint(400, 800)
    mouse_y = random.randint(200, 400)

    # Browsing phases: mimic a real user journey
    phases = [
        ("browse_home", random.randint(2, 4)),
        ("explore_products", random.randint(3, 6)),
        ("read_content", random.randint(2, 4)),
        ("target_action", random.randint(2, 4)),  # The actual bot task, disguised
        ("post_action_browse", random.randint(1, 3)),
    ]

    browse_endpoints = ["/home", "/about", "/products", "/blog", "/faq"]
    product_endpoints = ["/products/1", "/products/5", "/products/12", "/products/8", "/products/3"]
    target_endpoints = ["/api/products", "/api/products/1/reviews", "/api/search?q=deals"]

    for phase_name, num_events in phases:
        for _ in range(num_events):
            # Human-like delay between actions
            delay = human_like_delay()

            # Occasionally add a longer "thinking" pause (10-20% chance)
            if random.random() < 0.12:
                delay += random.uniform(3000, 8000)

            # Rare distraction (phone check, etc.) — 5% chance
            if random.random() < 0.05:
                delay += random.uniform(10000, 20000)

            current_time += timedelta(milliseconds=delay)

            # Determine event based on phase
            if phase_name == "browse_home":
                event_type = random.choice(["navigation", "scroll", "click"])
                endpoint = random.choice(browse_endpoints)
            elif phase_name == "explore_products":
                event_type = random.choice(["click", "scroll", "click", "navigation"])
                endpoint = random.choice(product_endpoints + browse_endpoints[:2])
            elif phase_name == "read_content":
                event_type = random.choice(["scroll", "scroll", "scroll", "click"])
                endpoint = random.choice(product_endpoints)
            elif phase_name == "target_action":
                # This is where the bot does its real work, but disguised
                event_type = random.choice(["navigation", "click", "scroll"])
                endpoint = random.choice(target_endpoints + product_endpoints[:2])
            else:
                event_type = random.choice(["scroll", "click", "navigation"])
                endpoint = random.choice(browse_endpoints)

            # Generate natural mouse movement
            target_x = random.randint(100, 1800)
            target_y = random.randint(100, 1000)
            path = generate_curved_mouse_path(mouse_x, mouse_y, target_x, target_y)
            final_point = path[-1]

            # Calculate speed based on distance and time (realistic: 300-1000 px/s)
            distance = math.sqrt((target_x - mouse_x) ** 2 + (target_y - mouse_y) ** 2)
            move_time = random.uniform(200, 600)  # ms to move mouse
            speed = distance / (move_time / 1000) if move_time > 0 else 500
            speed = max(200, min(speed, 1200))  # Clamp to human range

            mouse_data = {
                "x": final_point[0],
                "y": final_point[1],
                "speed": round(speed, 1),
                "hasCurve": True,  # Always curve like a human
            }

            # Keyboard data only for form/search interactions
            keyboard_data = None
            if event_type == "keypress" or (endpoint.startswith("/api/search") and random.random() < 0.5):
                keyboard_data = human_typing_pattern(random.randint(5, 30))
                event_type = "keypress"

            # Duration: humans spend time on actions
            if event_type == "scroll":
                duration = random.randint(1000, 5000)
            elif event_type == "click":
                duration = random.randint(200, 1500)
            else:
                duration = random.randint(500, 3000)

            events.append({
                "sessionId": session_id,
                "userId": user_id,
                "timestamp": current_time.strftime("%Y-%m-%dT%H:%M:%S.") + f"{current_time.microsecond // 1000:03d}Z",
                "eventType": event_type,
                "endpoint": endpoint,
                "durationMs": duration,
                "mouse": mouse_data,
                "keyboard": keyboard_data,
            })

            # Update mouse position
            mouse_x = final_point[0]
            mouse_y = final_point[1]

    return {
        "sessionId": session_id,
        "userId": user_id,
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        "ipAddress": f"192.168.{random.randint(1, 10)}.{random.randint(1, 254)}",
        "events": events,
        "label": "challenge_bot",
        "evasion_techniques": [
            "log-normal timing distribution",
            "bezier-curved mouse paths",
            "human typing with real error rates",
            "browsing phases (explore before targeting)",
            "thinking pauses and distractions",
            "realistic mouse speed (300-1000 px/s)",
            "natural endpoint progression",
        ],
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    base_time = datetime(2026, 5, 28, 14, 0, 0, tzinfo=timezone.utc)

    print("=" * 70)
    print("  CHALLENGE BOT GENERATOR")
    print("  Creating advanced evasion bots and testing against detection engine")
    print("=" * 70)

    # Generate 50 challenge bot sessions
    num_bots = 50
    sessions = []
    print(f"\nGenerating {num_bots} challenge bot sessions...")

    for i in range(num_bots):
        session = generate_challenge_bot_session(i, base_time)
        sessions.append(session)

    # Save the raw sessions
    sessions_path = os.path.join(OUTPUT_DIR, "challenge_bot_sessions.json")
    with open(sessions_path, "w", encoding="utf-8") as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)
    print(f"Saved {num_bots} sessions to {sessions_path}")

    # Send each to the detection engine
    print(f"\nSending to detection engine at {API_URL}...")
    results = []
    detected_count = 0

    for i, session in enumerate(sessions):
        # Remove label and evasion_techniques before sending
        clean = {k: v for k, v in session.items() if k not in ("label", "evasion_techniques")}

        try:
            resp = requests.post(API_URL, json=clean, timeout=10)
            if resp.status_code == 200:
                result = resp.json()
                result["groundTruth"] = "challenge_bot"
                result["evasion_techniques"] = session["evasion_techniques"]
                results.append(result)

                if result["isLikelyAiAgent"]:
                    detected_count += 1
                    status = "CAUGHT"
                else:
                    status = "EVADED"

                print(f"  Bot {i:03d}: score={result['aiProbabilityScore']:.4f} [{status}]")
            else:
                print(f"  Bot {i:03d}: API error {resp.status_code}")
        except Exception as e:
            print(f"  Bot {i:03d}: Connection error: {e}")

    # Save detection results
    results_path = os.path.join(OUTPUT_DIR, "detection_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  CHALLENGE BOT RESULTS")
    print(f"{'=' * 70}")
    print(f"\n  Total challenge bots: {num_bots}")
    print(f"  Detected (caught):    {detected_count} ({detected_count/num_bots*100:.1f}%)")
    print(f"  Evaded (undetected):  {num_bots - detected_count} ({(num_bots-detected_count)/num_bots*100:.1f}%)")

    if results:
        scores = [r["aiProbabilityScore"] for r in results]
        print(f"\n  Score distribution:")
        print(f"    Min:  {min(scores):.4f}")
        print(f"    Max:  {max(scores):.4f}")
        print(f"    Avg:  {sum(scores)/len(scores):.4f}")
        print(f"    Threshold: 0.65")

        # Signal breakdown
        print(f"\n  Average signal scores (lower = better evasion):")
        signal_totals = {}
        for r in results:
            for s in r.get("signals", []):
                name = s["signalName"]
                signal_totals.setdefault(name, []).append(s["score"])

        for name, scores_list in sorted(signal_totals.items()):
            avg = sum(scores_list) / len(scores_list)
            print(f"    {name:25} avg={avg:.3f}")

    # Save summary
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_bots": num_bots,
        "detected": detected_count,
        "evaded": num_bots - detected_count,
        "evasion_rate": round((num_bots - detected_count) / num_bots * 100, 1),
        "avg_score": round(sum(r["aiProbabilityScore"] for r in results) / len(results), 4) if results else 0,
        "threshold": 0.65,
        "techniques_used": sessions[0]["evasion_techniques"] if sessions else [],
    }
    summary_path = os.path.join(OUTPUT_DIR, "challenge_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n  Data saved to {OUTPUT_DIR}/:")
    print(f"    challenge_bot_sessions.json  - raw bot activity data")
    print(f"    detection_results.json       - what the engine said about each bot")
    print(f"    challenge_summary.json       - summary stats")
    print(f"\n{'=' * 70}")


if __name__ == "__main__":
    main()
