"""
Stress Test — Run 100 diverse bot sessions + 50 human sessions against the identifier.

Generates randomized variations of each bot type to test robustness.
Each bot type has 20 variants with slightly different parameters.
"""

import json
import os
import random
import time
from datetime import datetime, timedelta, timezone

import requests

API_URL = "http://localhost:5000/api/detection/analyze"
OUTPUT_DIR = "./drission_bot/stress_test_results"


def ts(base, offset_ms):
    t = base + timedelta(milliseconds=offset_ms)
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}Z"


def gen_speed_scraper(idx):
    """Variant speed scrapers with different speeds and targets."""
    base = datetime(2026, 5, 28, 20, 0, 0, tzinfo=timezone.utc)
    events = []
    offset = 0
    speed_range = random.uniform(30, 250)
    num = random.randint(10, 40)
    endpoints = ["/api/products", "/api/users", "/api/orders", "/api/search",
                 "/products/1", "/products/2", "/api/inventory", "/api/prices"]

    for i in range(num):
        offset += random.uniform(speed_range * 0.5, speed_range * 1.5)
        events.append({
            "sessionId": f"speed-{idx:03d}", "userId": f"scraper-{idx}",
            "timestamp": ts(base, offset),
            "eventType": random.choice(["api_call", "navigation"]),
            "endpoint": random.choice(endpoints),
            "durationMs": random.randint(5, 80),
            "mouse": {"x": random.randint(0, 1920), "y": random.randint(0, 1080),
                      "speed": random.uniform(3000, 12000), "hasCurve": False} if random.random() < 0.3 else None,
            "keyboard": None,
        })
    return {"sessionId": f"speed-{idx:03d}", "userId": f"scraper-{idx}",
            "userAgent": random.choice(["python-requests/2.31", "aiohttp/3.9", "curl/8.4", "Go-http-client/2.0"]),
            "ipAddress": f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            "events": events, "expected": "bot", "type": "Speed Scraper"}


def gen_stealth_crawler(idx):
    """Stealth crawlers that visit pages in order."""
    base = datetime(2026, 5, 28, 20, 5, 0, tzinfo=timezone.utc)
    events = []
    offset = 0
    num_pages = random.randint(8, 20)

    for i in range(num_pages):
        offset += random.lognormvariate(7.0 + random.uniform(-0.3, 0.3), 0.5)
        events.append({
            "sessionId": f"stealth-{idx:03d}", "userId": f"crawler-{idx}",
            "timestamp": ts(base, offset),
            "eventType": "navigation",
            "endpoint": f"/products/{i+1}",
            "durationMs": random.randint(500, 3000),
            "mouse": {"x": random.randint(100, 1800), "y": random.randint(100, 900),
                      "speed": random.gauss(750, 120), "hasCurve": True},
            "keyboard": None,
        })
    return {"sessionId": f"stealth-{idx:03d}", "userId": f"crawler-{idx}",
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0",
            "ipAddress": f"192.168.{random.randint(1,10)}.{random.randint(1,254)}",
            "events": events, "expected": "bot", "type": "Stealth Crawler"}


def gen_form_spammer(idx):
    """Form spammers with varying speeds."""
    base = datetime(2026, 5, 28, 20, 10, 0, tzinfo=timezone.utc)
    events = []
    offset = 0
    attempts = random.randint(5, 15)

    for _ in range(attempts):
        offset += random.uniform(200, 1000)
        events.append({
            "sessionId": f"spam-{idx:03d}", "userId": f"spammer-{idx}",
            "timestamp": ts(base, offset),
            "eventType": "navigation", "endpoint": "/login",
            "durationMs": random.randint(50, 300),
            "mouse": {"x": 500, "y": 400, "speed": random.uniform(2000, 8000), "hasCurve": False},
            "keyboard": None,
        })
        offset += random.uniform(100, 400)
        events.append({
            "sessionId": f"spam-{idx:03d}", "userId": f"spammer-{idx}",
            "timestamp": ts(base, offset),
            "eventType": "keypress", "endpoint": "/login",
            "durationMs": random.randint(100, 500),
            "mouse": None,
            "keyboard": {"interKeyDelayMs": random.uniform(8, 30), "burstLength": random.randint(15, 50), "errorRate": 0.0},
        })
        offset += random.uniform(50, 200)
        events.append({
            "sessionId": f"spam-{idx:03d}", "userId": f"spammer-{idx}",
            "timestamp": ts(base, offset),
            "eventType": "form_submit", "endpoint": "/api/auth/login",
            "durationMs": random.randint(10, 50),
            "mouse": {"x": 500, "y": 500, "speed": 5000, "hasCurve": False},
            "keyboard": None,
        })
    return {"sessionId": f"spam-{idx:03d}", "userId": f"spammer-{idx}",
            "userAgent": "Mozilla/5.0 (compatible; Bot/1.0)",
            "ipAddress": f"10.0.{random.randint(0,255)}.{random.randint(1,254)}",
            "events": events, "expected": "bot", "type": "Form Spammer"}


def gen_content_thief(idx):
    """Content thieves that systematically scroll through articles."""
    base = datetime(2026, 5, 28, 20, 15, 0, tzinfo=timezone.utc)
    events = []
    offset = 0
    articles = random.randint(4, 8)

    for a in range(articles):
        offset += random.uniform(800, 2500)
        events.append({
            "sessionId": f"thief-{idx:03d}", "userId": f"thief-{idx}",
            "timestamp": ts(base, offset),
            "eventType": "navigation", "endpoint": f"/blog/post-{a+1}",
            "durationMs": random.randint(300, 1500),
            "mouse": {"x": random.randint(300, 800), "y": 200, "speed": random.uniform(500, 1000), "hasCurve": random.random() < 0.4},
            "keyboard": None,
        })
        for s in range(random.randint(3, 6)):
            offset += random.uniform(600, 1400)
            events.append({
                "sessionId": f"thief-{idx:03d}", "userId": f"thief-{idx}",
                "timestamp": ts(base, offset),
                "eventType": "scroll", "endpoint": f"/blog/post-{a+1}",
                "durationMs": random.randint(200, 600),
                "mouse": {"x": 500, "y": 200 + s * 150, "speed": random.uniform(300, 700), "hasCurve": False},
                "keyboard": None,
            })
    return {"sessionId": f"thief-{idx:03d}", "userId": f"thief-{idx}",
            "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15",
            "ipAddress": f"172.16.{random.randint(0,255)}.{random.randint(1,254)}",
            "events": events, "expected": "bot", "type": "Content Thief"}


def gen_drission_bot(idx):
    """DrissionPage-style bots with consistent page load timing."""
    base = datetime(2026, 5, 28, 20, 20, 0, tzinfo=timezone.utc)
    events = []
    offset = 0
    page_load = random.gauss(6000, 500)  # Each bot has its own consistent load time
    pages = random.randint(6, 15)
    endpoints = ["/home", "/about", "/products", "/contact", "/faq", "/blog"]

    for i in range(pages):
        offset += random.gauss(page_load, page_load * 0.03)  # Very low jitter
        events.append({
            "sessionId": f"drission-{idx:03d}", "userId": f"drission-{idx}",
            "timestamp": ts(base, offset),
            "eventType": "navigation",
            "endpoint": random.choice(endpoints),
            "durationMs": int(page_load * random.uniform(0.9, 1.1)),
            "mouse": {"x": random.randint(100, 1200), "y": random.randint(100, 800),
                      "speed": random.uniform(800, 1500), "hasCurve": random.random() < 0.3},
            "keyboard": None,
        })
    return {"sessionId": f"drission-{idx:03d}", "userId": f"drission-{idx}",
            "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0",
            "ipAddress": f"192.168.{random.randint(1,20)}.{random.randint(1,254)}",
            "events": events, "expected": "bot", "type": "DrissionPage"}


def gen_human(idx):
    """Realistic human sessions with high variance."""
    base = datetime(2026, 5, 28, 20, 30, 0, tzinfo=timezone.utc)
    events = []
    offset = 0
    num = random.randint(5, 20)
    endpoints = ["/home", "/products", "/products/3", "/blog", "/cart", "/about", "/faq", "/contact"]
    last_ep = ""

    for i in range(num):
        if random.random() < 0.15:
            offset += random.uniform(5000, 20000)
        elif random.random() < 0.1:
            offset += random.uniform(10000, 35000)
        else:
            offset += random.lognormvariate(7.3, 0.7)

        event_type = random.choice(["click", "scroll", "navigation", "scroll", "click", "keypress"])

        # Humans revisit pages
        if random.random() < 0.2 and last_ep:
            ep = last_ep
        else:
            ep = random.choice(endpoints)
        last_ep = ep

        mouse = None
        if event_type != "keypress":
            mouse = {"x": random.randint(100, 1800), "y": random.randint(100, 1000),
                     "speed": random.gauss(650, 250), "hasCurve": random.random() < 0.88}

        keyboard = None
        if event_type == "keypress":
            keyboard = {"interKeyDelayMs": random.gauss(145, 55),
                        "burstLength": random.randint(2, 7),
                        "errorRate": random.uniform(0.03, 0.12)}

        events.append({
            "sessionId": f"human-{idx:03d}", "userId": f"user-{idx}",
            "timestamp": ts(base, offset),
            "eventType": event_type, "endpoint": ep,
            "durationMs": random.randint(500, 8000),
            "mouse": mouse, "keyboard": keyboard,
        })

    return {"sessionId": f"human-{idx:03d}", "userId": f"user-{idx}",
            "userAgent": random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0",
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5) Safari/605.1.15",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Firefox/126.0",
            ]),
            "ipAddress": f"192.168.{random.randint(1,10)}.{random.randint(1,254)}",
            "events": events, "expected": "human", "type": "Human"}


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 70)
    print("  STRESS TEST — 400 Sessions (50 variants × 6 bot types + 100 humans)")
    print("=" * 70)

    # Generate sessions — 50 variants of each bot type
    sessions = []
    for i in range(50):
        sessions.append(gen_speed_scraper(i))
    for i in range(50):
        sessions.append(gen_stealth_crawler(i))
    for i in range(50):
        sessions.append(gen_form_spammer(i))
    for i in range(50):
        sessions.append(gen_content_thief(i))
    for i in range(50):
        sessions.append(gen_drission_bot(i))
    for i in range(100):
        sessions.append(gen_human(i))

    random.shuffle(sessions)

    print(f"\n  Generated {len(sessions)} sessions")
    print(f"  Sending to detection engine...\n")

    # Test each
    results = []
    for i, session in enumerate(sessions):
        clean = {k: v for k, v in session.items() if k not in ("expected", "type")}
        try:
            resp = requests.post(API_URL, json=clean, timeout=5)
            if resp.status_code == 200:
                r = resp.json()
                results.append({
                    "sessionId": session["sessionId"],
                    "type": session["type"],
                    "expected": session["expected"],
                    "detected": r["isLikelyAiAgent"],
                    "score": r["aiProbabilityScore"],
                })
            else:
                results.append({"sessionId": session["sessionId"], "type": session["type"],
                                "expected": session["expected"], "detected": None, "score": 0, "error": resp.status_code})
        except Exception as e:
            results.append({"sessionId": session["sessionId"], "type": session["type"],
                            "expected": session["expected"], "detected": None, "score": 0, "error": str(e)})

        if (i + 1) % 25 == 0:
            print(f"  Processed {i+1}/{len(sessions)}...")

    # Analyze results
    print(f"\n{'=' * 70}")
    print(f"  RESULTS")
    print(f"{'=' * 70}")

    # By type
    types = {}
    for r in results:
        t = r["type"]
        if t not in types:
            types[t] = {"total": 0, "correct": 0, "scores": []}
        types[t]["total"] += 1
        types[t]["scores"].append(r["score"])

        expected_bot = r["expected"] == "bot"
        detected_bot = r.get("detected", False)
        if expected_bot == detected_bot:
            types[t]["correct"] += 1

    print(f"\n  {'Type':<20} {'Total':>6} {'Correct':>8} {'Accuracy':>9} {'Avg Score':>10}")
    print(f"  {'─' * 60}")

    total_correct = 0
    total_all = 0
    for t, data in sorted(types.items()):
        acc = data["correct"] / data["total"] * 100
        avg = sum(data["scores"]) / len(data["scores"])
        print(f"  {t:<20} {data['total']:>6} {data['correct']:>8} {acc:>8.1f}% {avg:>9.3f}")
        total_correct += data["correct"]
        total_all += data["total"]

    print(f"  {'─' * 60}")
    print(f"  {'TOTAL':<20} {total_all:>6} {total_correct:>8} {total_correct/total_all*100:>8.1f}%")

    # Confusion matrix
    tp = sum(1 for r in results if r["expected"] == "bot" and r.get("detected") == True)
    fn = sum(1 for r in results if r["expected"] == "bot" and r.get("detected") == False)
    tn = sum(1 for r in results if r["expected"] == "human" and r.get("detected") == False)
    fp = sum(1 for r in results if r["expected"] == "human" and r.get("detected") == True)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print(f"\n  Confusion Matrix:")
    print(f"  {'':20} Pred Human  Pred Bot")
    print(f"  {'Actual Human':<20} {tn:>9}  {fp:>8}")
    print(f"  {'Actual Bot':<20} {fn:>9}  {tp:>8}")

    print(f"\n  Precision: {precision:.3f}")
    print(f"  Recall:    {recall:.3f}")
    print(f"  F1 Score:  {f1:.3f}")
    print(f"  Accuracy:  {total_correct/total_all:.3f}")

    # Worst misses
    missed_bots = [r for r in results if r["expected"] == "bot" and r.get("detected") == False]
    if missed_bots:
        print(f"\n  Missed bots ({len(missed_bots)}):")
        for r in sorted(missed_bots, key=lambda x: x["score"], reverse=True)[:5]:
            print(f"    {r['type']:<20} {r['sessionId']:<20} score={r['score']:.4f}")

    false_alarms = [r for r in results if r["expected"] == "human" and r.get("detected") == True]
    if false_alarms:
        print(f"\n  False alarms ({len(false_alarms)}):")
        for r in sorted(false_alarms, key=lambda x: x["score"], reverse=True)[:5]:
            print(f"    {r['type']:<20} {r['sessionId']:<20} score={r['score']:.4f}")

    print(f"\n{'=' * 70}")

    # Save
    output_path = os.path.join(OUTPUT_DIR, "stress_test_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"summary": {"total": total_all, "correct": total_correct,
                                "precision": precision, "recall": recall, "f1": f1},
                   "by_type": types, "results": results}, f, indent=2)
    print(f"  Saved to {output_path}")


if __name__ == "__main__":
    main()
