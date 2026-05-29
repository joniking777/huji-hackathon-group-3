"""
Deep DrissionPage Detection Test — 200 DrissionPage variants + 50 humans.

Tests multiple evasion strategies that DrissionPage bots might use:
1. Standard DrissionPage (consistent page load timing)
2. DrissionPage with randomized delays (trying to evade timing detection)
3. DrissionPage with fake mouse curves (trying to look human)
4. DrissionPage with fake scrolling (adding scroll events)
5. DrissionPage with mixed actions (adding fake keypresses)
6. DrissionPage slow mode (longer waits between pages)
7. DrissionPage with revisits (going back to pages)
8. DrissionPage stealth (combining multiple evasion techniques)

Produces detailed statistics per variant type.

Usage:
    python drission_bot/drission_deep_test.py

Requires:
    - AISecutity API running on http://localhost:5000
"""

import json
import math
import os
import random
import statistics
import time
from datetime import datetime, timedelta, timezone

import requests

API_URL = "http://localhost:5000/api/detection/analyze"
OUTPUT_DIR = "./drission_bot/drission_deep_results"


def ts(base, offset_ms):
    t = base + timedelta(milliseconds=offset_ms)
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}Z"


# ============================================================
# VARIANT 1: Standard DrissionPage
# Consistent ~6s page loads, high mouse speed, no curves
# ============================================================
def gen_drission_standard(idx):
    base = datetime(2026, 5, 28, 20, 0, 0, tzinfo=timezone.utc)
    events = []
    offset = 0
    page_load = random.gauss(6000, 500)
    pages = random.randint(8, 15)
    endpoints = ["/home", "/about", "/products", "/contact", "/faq",
                 "/blog", "/products/1", "/products/2", "/products/3"]

    for i in range(pages):
        offset += random.gauss(page_load, page_load * 0.03)
        events.append({
            "sessionId": f"drission-std-{idx:03d}",
            "userId": f"drission-std-{idx}",
            "timestamp": ts(base, offset),
            "eventType": "navigation",
            "endpoint": random.choice(endpoints),
            "durationMs": int(page_load * random.uniform(0.9, 1.1)),
            "mouse": {
                "x": random.randint(100, 1200),
                "y": random.randint(100, 800),
                "speed": random.uniform(800, 1500),
                "hasCurve": random.random() < 0.3,
            },
            "keyboard": None,
        })
    return {
        "sessionId": f"drission-std-{idx:03d}",
        "userId": f"drission-std-{idx}",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        "ipAddress": f"192.168.{random.randint(1,20)}.{random.randint(1,254)}",
        "events": events,
        "expected": "bot",
        "type": "DrissionPage Standard",
    }


# ============================================================
# VARIANT 2: DrissionPage with Randomized Delays
# Tries to evade timing detection by adding random waits
# ============================================================
def gen_drission_random_delays(idx):
    base = datetime(2026, 5, 28, 20, 5, 0, tzinfo=timezone.utc)
    events = []
    offset = 0
    pages = random.randint(8, 14)
    endpoints = ["/home", "/about", "/products", "/contact", "/faq",
                 "/blog", "/products/1", "/products/2", "/cart"]

    for i in range(pages):
        # Trying to randomize: uniform distribution instead of gaussian
        offset += random.uniform(2000, 10000)
        events.append({
            "sessionId": f"drission-rnd-{idx:03d}",
            "userId": f"drission-rnd-{idx}",
            "timestamp": ts(base, offset),
            "eventType": "navigation",
            "endpoint": random.choice(endpoints),
            "durationMs": random.randint(1000, 5000),
            "mouse": {
                "x": random.randint(100, 1600),
                "y": random.randint(100, 900),
                "speed": random.uniform(700, 1400),
                "hasCurve": random.random() < 0.3,
            },
            "keyboard": None,
        })
    return {
        "sessionId": f"drission-rnd-{idx:03d}",
        "userId": f"drission-rnd-{idx}",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        "ipAddress": f"10.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,254)}",
        "events": events,
        "expected": "bot",
        "type": "DrissionPage RandomDelay",
    }


# ============================================================
# VARIANT 3: DrissionPage with Fake Mouse Curves
# Adds hasCurve=True and moderate speeds to look human
# ============================================================
def gen_drission_fake_curves(idx):
    base = datetime(2026, 5, 28, 20, 10, 0, tzinfo=timezone.utc)
    events = []
    offset = 0
    page_load = random.gauss(5500, 400)
    pages = random.randint(7, 13)
    endpoints = ["/home", "/products", "/products/1", "/products/2",
                 "/cart", "/about", "/blog/post-1"]

    for i in range(pages):
        offset += random.gauss(page_load, page_load * 0.04)
        events.append({
            "sessionId": f"drission-crv-{idx:03d}",
            "userId": f"drission-crv-{idx}",
            "timestamp": ts(base, offset),
            "eventType": random.choice(["navigation", "click"]),
            "endpoint": random.choice(endpoints),
            "durationMs": int(page_load * random.uniform(0.85, 1.15)),
            "mouse": {
                "x": random.randint(200, 1600),
                "y": random.randint(150, 850),
                "speed": random.gauss(650, 150),  # Trying to match human speed
                "hasCurve": True,  # Always curves
            },
            "keyboard": None,
        })
    return {
        "sessionId": f"drission-crv-{idx:03d}",
        "userId": f"drission-crv-{idx}",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        "ipAddress": f"192.168.{random.randint(1,15)}.{random.randint(1,254)}",
        "events": events,
        "expected": "bot",
        "type": "DrissionPage FakeCurves",
    }


# ============================================================
# VARIANT 4: DrissionPage with Fake Scrolling
# Adds scroll events between navigations to simulate reading
# ============================================================
def gen_drission_fake_scroll(idx):
    base = datetime(2026, 5, 28, 20, 15, 0, tzinfo=timezone.utc)
    events = []
    offset = 0
    page_load = random.gauss(6200, 300)
    pages = random.randint(6, 10)
    endpoints = ["/home", "/products", "/blog/post-1", "/blog/post-2",
                 "/about", "/products/3", "/faq"]

    for i in range(pages):
        offset += random.gauss(page_load, page_load * 0.03)
        ep = random.choice(endpoints)
        events.append({
            "sessionId": f"drission-scr-{idx:03d}",
            "userId": f"drission-scr-{idx}",
            "timestamp": ts(base, offset),
            "eventType": "navigation",
            "endpoint": ep,
            "durationMs": int(page_load * random.uniform(0.9, 1.1)),
            "mouse": {
                "x": random.randint(200, 1400),
                "y": random.randint(100, 400),
                "speed": random.uniform(900, 1300),
                "hasCurve": random.random() < 0.4,
            },
            "keyboard": None,
        })
        # Add 2-3 fake scrolls
        for s in range(random.randint(2, 3)):
            offset += random.uniform(800, 1500)
            events.append({
                "sessionId": f"drission-scr-{idx:03d}",
                "userId": f"drission-scr-{idx}",
                "timestamp": ts(base, offset),
                "eventType": "scroll",
                "endpoint": ep,
                "durationMs": random.randint(200, 600),
                "mouse": {
                    "x": random.randint(300, 800),
                    "y": 200 + s * 200,  # Linear scroll pattern (bot tell)
                    "speed": random.uniform(400, 700),
                    "hasCurve": False,
                },
                "keyboard": None,
            })
    return {
        "sessionId": f"drission-scr-{idx:03d}",
        "userId": f"drission-scr-{idx}",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        "ipAddress": f"172.16.{random.randint(0,255)}.{random.randint(1,254)}",
        "events": events,
        "expected": "bot",
        "type": "DrissionPage FakeScroll",
    }


# ============================================================
# VARIANT 5: DrissionPage with Fake Keypresses
# Adds keyboard events to simulate typing (search, forms)
# ============================================================
def gen_drission_fake_typing(idx):
    base = datetime(2026, 5, 28, 20, 20, 0, tzinfo=timezone.utc)
    events = []
    offset = 0
    page_load = random.gauss(5800, 400)
    pages = random.randint(7, 12)
    endpoints = ["/home", "/products", "/search", "/products/1",
                 "/cart", "/checkout", "/blog"]

    for i in range(pages):
        offset += random.gauss(page_load, page_load * 0.035)
        ep = random.choice(endpoints)
        events.append({
            "sessionId": f"drission-typ-{idx:03d}",
            "userId": f"drission-typ-{idx}",
            "timestamp": ts(base, offset),
            "eventType": "navigation",
            "endpoint": ep,
            "durationMs": int(page_load * random.uniform(0.9, 1.1)),
            "mouse": {
                "x": random.randint(100, 1500),
                "y": random.randint(100, 800),
                "speed": random.uniform(850, 1400),
                "hasCurve": random.random() < 0.35,
            },
            "keyboard": None,
        })
        # Add fake typing every 3rd page
        if i % 3 == 1:
            offset += random.uniform(500, 1500)
            events.append({
                "sessionId": f"drission-typ-{idx:03d}",
                "userId": f"drission-typ-{idx}",
                "timestamp": ts(base, offset),
                "eventType": "keypress",
                "endpoint": ep,
                "durationMs": random.randint(300, 800),
                "mouse": None,
                "keyboard": {
                    "interKeyDelayMs": random.uniform(40, 80),  # Fast but not superhuman
                    "burstLength": random.randint(5, 15),
                    "errorRate": 0.0,  # Still no errors (bot tell)
                },
            })
    return {
        "sessionId": f"drission-typ-{idx:03d}",
        "userId": f"drission-typ-{idx}",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        "ipAddress": f"10.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,254)}",
        "events": events,
        "expected": "bot",
        "type": "DrissionPage FakeTyping",
    }


# ============================================================
# VARIANT 6: DrissionPage Slow Mode
# Longer waits (8-12s) to avoid speed detection
# ============================================================
def gen_drission_slow(idx):
    base = datetime(2026, 5, 28, 20, 25, 0, tzinfo=timezone.utc)
    events = []
    offset = 0
    page_load = random.gauss(10000, 800)  # Much slower
    pages = random.randint(5, 9)
    endpoints = ["/home", "/products", "/about", "/blog", "/contact",
                 "/products/1", "/products/2"]

    for i in range(pages):
        offset += random.gauss(page_load, page_load * 0.04)
        events.append({
            "sessionId": f"drission-slw-{idx:03d}",
            "userId": f"drission-slw-{idx}",
            "timestamp": ts(base, offset),
            "eventType": "navigation",
            "endpoint": random.choice(endpoints),
            "durationMs": int(page_load * random.uniform(0.85, 1.15)),
            "mouse": {
                "x": random.randint(200, 1400),
                "y": random.randint(150, 800),
                "speed": random.uniform(700, 1200),
                "hasCurve": random.random() < 0.4,
            },
            "keyboard": None,
        })
    return {
        "sessionId": f"drission-slw-{idx:03d}",
        "userId": f"drission-slw-{idx}",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        "ipAddress": f"192.168.{random.randint(1,20)}.{random.randint(1,254)}",
        "events": events,
        "expected": "bot",
        "type": "DrissionPage Slow",
    }


# ============================================================
# VARIANT 7: DrissionPage with Revisits
# Goes back to previously visited pages to look human
# ============================================================
def gen_drission_revisits(idx):
    base = datetime(2026, 5, 28, 20, 30, 0, tzinfo=timezone.utc)
    events = []
    offset = 0
    page_load = random.gauss(6000, 400)
    pages = random.randint(8, 14)
    endpoints = ["/home", "/products", "/about", "/blog", "/contact",
                 "/products/1", "/cart"]
    visited = []

    for i in range(pages):
        offset += random.gauss(page_load, page_load * 0.035)
        # 25% chance to revisit a previous page
        if visited and random.random() < 0.25:
            ep = random.choice(visited)
        else:
            ep = random.choice(endpoints)
        visited.append(ep)

        events.append({
            "sessionId": f"drission-rev-{idx:03d}",
            "userId": f"drission-rev-{idx}",
            "timestamp": ts(base, offset),
            "eventType": "navigation",
            "endpoint": ep,
            "durationMs": int(page_load * random.uniform(0.9, 1.1)),
            "mouse": {
                "x": random.randint(100, 1500),
                "y": random.randint(100, 800),
                "speed": random.uniform(800, 1400),
                "hasCurve": random.random() < 0.35,
            },
            "keyboard": None,
        })
    return {
        "sessionId": f"drission-rev-{idx:03d}",
        "userId": f"drission-rev-{idx}",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        "ipAddress": f"192.168.{random.randint(1,20)}.{random.randint(1,254)}",
        "events": events,
        "expected": "bot",
        "type": "DrissionPage Revisits",
    }


# ============================================================
# VARIANT 8: DrissionPage Full Stealth
# Combines ALL evasion techniques: random delays, curves,
# scrolls, typing with errors, revisits, idle gaps
# ============================================================
def gen_drission_stealth(idx):
    base = datetime(2026, 5, 28, 20, 35, 0, tzinfo=timezone.utc)
    events = []
    offset = 0
    pages = random.randint(8, 14)
    endpoints = ["/home", "/products", "/about", "/blog", "/contact",
                 "/products/1", "/products/2", "/cart", "/faq"]
    visited = []

    for i in range(pages):
        # Log-normal-ish timing (trying to mimic human distribution)
        if random.random() < 0.15:
            offset += random.uniform(8000, 18000)  # Fake idle gap
        else:
            offset += random.lognormvariate(8.0, 0.3)  # ~3000ms with some variance

        # Revisit sometimes
        if visited and random.random() < 0.2:
            ep = random.choice(visited)
        else:
            ep = random.choice(endpoints)
        visited.append(ep)

        events.append({
            "sessionId": f"drission-sth-{idx:03d}",
            "userId": f"drission-sth-{idx}",
            "timestamp": ts(base, offset),
            "eventType": random.choice(["navigation", "click"]),
            "endpoint": ep,
            "durationMs": random.randint(1500, 5000),
            "mouse": {
                "x": random.randint(200, 1600),
                "y": random.randint(150, 850),
                "speed": random.gauss(650, 180),  # Human-like speed
                "hasCurve": random.random() < 0.85,  # Mostly curves
            },
            "keyboard": None,
        })

        # Add scroll on some pages
        if random.random() < 0.4:
            offset += random.uniform(1000, 3000)
            events.append({
                "sessionId": f"drission-sth-{idx:03d}",
                "userId": f"drission-sth-{idx}",
                "timestamp": ts(base, offset),
                "eventType": "scroll",
                "endpoint": ep,
                "durationMs": random.randint(500, 2000),
                "mouse": {
                    "x": random.randint(300, 1200),
                    "y": random.randint(200, 700),
                    "speed": random.gauss(500, 150),
                    "hasCurve": True,
                },
                "keyboard": None,
            })

        # Add typing on some pages (with fake errors!)
        if random.random() < 0.2:
            offset += random.uniform(1500, 4000)
            events.append({
                "sessionId": f"drission-sth-{idx:03d}",
                "userId": f"drission-sth-{idx}",
                "timestamp": ts(base, offset),
                "eventType": "keypress",
                "endpoint": ep,
                "durationMs": random.randint(2000, 5000),
                "mouse": None,
                "keyboard": {
                    "interKeyDelayMs": random.gauss(130, 40),  # Human-like
                    "burstLength": random.randint(3, 8),
                    "errorRate": random.uniform(0.03, 0.08),  # Fake errors!
                },
            })
    return {
        "sessionId": f"drission-sth-{idx:03d}",
        "userId": f"drission-sth-{idx}",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        "ipAddress": f"192.168.{random.randint(1,20)}.{random.randint(1,254)}",
        "events": events,
        "expected": "bot",
        "type": "DrissionPage Stealth",
    }


# ============================================================
# HUMAN CONTROL — realistic human sessions
# ============================================================
def gen_human(idx):
    base = datetime(2026, 5, 28, 20, 40, 0, tzinfo=timezone.utc)
    events = []
    offset = 0
    num = random.randint(6, 20)
    endpoints = ["/home", "/products", "/products/3", "/blog", "/cart",
                 "/about", "/faq", "/contact", "/blog/post-1", "/products/5"]
    last_ep = ""

    for i in range(num):
        # Human timing: log-normal with occasional long pauses
        if random.random() < 0.15:
            offset += random.uniform(5000, 25000)  # Distracted
        elif random.random() < 0.08:
            offset += random.uniform(15000, 45000)  # Very distracted
        else:
            offset += random.lognormvariate(7.5, 0.8)

        event_type = random.choice(["click", "scroll", "navigation",
                                     "scroll", "click", "keypress"])

        # Humans revisit pages often
        if random.random() < 0.25 and last_ep:
            ep = last_ep
        else:
            ep = random.choice(endpoints)
        last_ep = ep

        mouse = None
        if event_type != "keypress":
            mouse = {
                "x": random.randint(100, 1800),
                "y": random.randint(100, 1000),
                "speed": random.gauss(650, 250),
                "hasCurve": random.random() < 0.88,
            }

        keyboard = None
        if event_type == "keypress":
            keyboard = {
                "interKeyDelayMs": random.gauss(145, 55),
                "burstLength": random.randint(2, 7),
                "errorRate": random.uniform(0.03, 0.12),
            }

        events.append({
            "sessionId": f"human-ctrl-{idx:03d}",
            "userId": f"human-{idx}",
            "timestamp": ts(base, offset),
            "eventType": event_type,
            "endpoint": ep,
            "durationMs": random.randint(500, 8000),
            "mouse": mouse,
            "keyboard": keyboard,
        })

    return {
        "sessionId": f"human-ctrl-{idx:03d}",
        "userId": f"human-{idx}",
        "userAgent": random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5) AppleWebKit/605.1.15 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Gecko/20100101 Firefox/126.0",
        ]),
        "ipAddress": f"192.168.{random.randint(1,10)}.{random.randint(1,254)}",
        "events": events,
        "expected": "human",
        "type": "Human",
    }


# ============================================================
# MAIN — Run all tests and produce statistics
# ============================================================
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 70)
    print("  🔬 DEEP DrissionPage DETECTION TEST")
    print("  130 sessions: 100 DrissionPage variants + 30 humans")
    print("=" * 70)

    # Generate sessions — 12-13 of each DrissionPage variant + 30 humans
    sessions = []
    generators = [
        ("DrissionPage Standard", gen_drission_standard, 13),
        ("DrissionPage RandomDelay", gen_drission_random_delays, 13),
        ("DrissionPage FakeCurves", gen_drission_fake_curves, 12),
        ("DrissionPage FakeScroll", gen_drission_fake_scroll, 13),
        ("DrissionPage FakeTyping", gen_drission_fake_typing, 12),
        ("DrissionPage Slow", gen_drission_slow, 13),
        ("DrissionPage Revisits", gen_drission_revisits, 12),
        ("DrissionPage Stealth", gen_drission_stealth, 12),
        ("Human", gen_human, 30),
    ]

    for name, gen_fn, count in generators:
        for i in range(count):
            sessions.append(gen_fn(i))

    random.shuffle(sessions)

    print(f"\n  Generated {len(sessions)} sessions:")
    for name, _, count in generators:
        print(f"    {name:<30} x{count}")
    print(f"\n  Sending to detection engine at {API_URL}...")
    print()

    # Run tests — server now allows 600 req/min
    results = []
    errors = 0
    start_time = time.time()

    for i, session in enumerate(sessions):
        clean = {k: v for k, v in session.items() if k not in ("expected", "type")}

        try:
            resp = requests.post(API_URL, json=clean, timeout=10)
            if resp.status_code == 200:
                r = resp.json()
                results.append({
                    "sessionId": session["sessionId"],
                    "type": session["type"],
                    "expected": session["expected"],
                    "detected": r.get("isLikelyAiAgent", False),
                    "score": r.get("aiProbabilityScore", 0),
                    "action": r.get("recommendedAction", ""),
                    "signals": r.get("signals", []),
                })
            else:
                errors += 1
                results.append({
                    "sessionId": session["sessionId"],
                    "type": session["type"],
                    "expected": session["expected"],
                    "detected": None, "score": 0, "error": resp.status_code,
                })
        except Exception as e:
            errors += 1
            results.append({
                "sessionId": session["sessionId"],
                "type": session["type"],
                "expected": session["expected"],
                "detected": None, "score": 0, "error": str(e),
            })

        if (i + 1) % 25 == 0:
            elapsed = time.time() - start_time
            valid = sum(1 for r in results if r.get("detected") is not None)
            print(f"  [{i+1:>3}/{len(sessions)}] "
                  f"({elapsed:.1f}s, {valid} valid, {errors} errors)")

        time.sleep(0.05)  # Small gap

    elapsed = time.time() - start_time
    print(f"\n  Done in {elapsed:.1f}s ({errors} errors)")


    # ============================================================
    # STATISTICS
    # ============================================================
    valid_results = [r for r in results if r.get("detected") is not None]

    if not valid_results:
        print("\n  ❌ No valid results! Is the server running?")
        print(f"     Start: cd AISecutity/AISecutity && dotnet run --urls http://localhost:5000")
        return

    print(f"\n{'=' * 70}")
    print(f"  📊 RESULTS — {len(valid_results)} valid / {len(results)} total")
    print(f"{'=' * 70}")

    # Group by type
    by_type = {}
    for r in valid_results:
        t = r["type"]
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(r)

    # Per-type statistics
    print(f"\n  {'Type':<30} {'N':>4} {'Caught':>7} {'Rate':>7} "
          f"{'Avg':>7} {'Min':>7} {'Max':>7} {'StdDev':>7}")
    print(f"  {'─' * 85}")

    type_stats = {}
    for t in sorted(by_type.keys()):
        group = by_type[t]
        scores = [r["score"] for r in group]
        is_bot_type = group[0]["expected"] == "bot"

        if is_bot_type:
            caught = sum(1 for r in group if r["detected"])
            rate = caught / len(group) * 100
        else:
            caught = sum(1 for r in group if not r["detected"])  # Correct = NOT detected
            rate = caught / len(group) * 100

        avg_score = statistics.mean(scores) if scores else 0
        min_score = min(scores) if scores else 0
        max_score = max(scores) if scores else 0
        std_score = statistics.stdev(scores) if len(scores) > 1 else 0

        label = f"{'🚨' if is_bot_type else '✅'} {rate:.0f}%"
        print(f"  {t:<30} {len(group):>4} {caught:>5}/{len(group):<2} {label:>7} "
              f"{avg_score:>7.4f} {min_score:>7.4f} {max_score:>7.4f} {std_score:>7.4f}")

        type_stats[t] = {
            "count": len(group),
            "caught": caught,
            "rate": rate,
            "avg_score": avg_score,
            "min_score": min_score,
            "max_score": max_score,
            "std_score": std_score,
            "scores": scores,
        }

    # Overall DrissionPage stats
    drission_results = [r for r in valid_results if "DrissionPage" in r["type"]]
    human_results = [r for r in valid_results if r["type"] == "Human"]

    if drission_results:
        dr_caught = sum(1 for r in drission_results if r["detected"])
        dr_total = len(drission_results)
        dr_scores = [r["score"] for r in drission_results]

        print(f"\n  {'─' * 85}")
        print(f"  {'ALL DrissionPage':<30} {dr_total:>4} "
              f"{dr_caught:>5}/{dr_total:<2} 🚨 {dr_caught/dr_total*100:.1f}% "
              f"{statistics.mean(dr_scores):>7.4f} "
              f"{min(dr_scores):>7.4f} {max(dr_scores):>7.4f} "
              f"{statistics.stdev(dr_scores):>7.4f}")

    if human_results:
        h_correct = sum(1 for r in human_results if not r["detected"])
        h_total = len(human_results)
        h_scores = [r["score"] for r in human_results]
        h_fp = h_total - h_correct

        print(f"  {'ALL Human':<30} {h_total:>4} "
              f"{h_correct:>5}/{h_total:<2} ✅ {h_correct/h_total*100:.1f}% "
              f"{statistics.mean(h_scores):>7.4f} "
              f"{min(h_scores):>7.4f} {max(h_scores):>7.4f} "
              f"{statistics.stdev(h_scores):>7.4f}")


    # Confusion matrix
    tp = sum(1 for r in valid_results if r["expected"] == "bot" and r["detected"])
    fn = sum(1 for r in valid_results if r["expected"] == "bot" and not r["detected"])
    tn = sum(1 for r in valid_results if r["expected"] == "human" and not r["detected"])
    fp = sum(1 for r in valid_results if r["expected"] == "human" and r["detected"])

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (tp + tn) / len(valid_results) if valid_results else 0

    print(f"\n\n  {'═' * 70}")
    print(f"  📈 OVERALL METRICS")
    print(f"  {'═' * 70}")
    print(f"\n  Confusion Matrix (DrissionPage bots vs Humans):")
    print(f"  {'':25} Predicted Human  Predicted Bot")
    print(f"  {'Actual Human':<25} {tn:>14}  {fp:>13}")
    print(f"  {'Actual Bot (Drission)':<25} {fn:>14}  {tp:>13}")
    print(f"\n  Precision:  {precision:.4f}  (of those flagged as bot, how many are actually bots)")
    print(f"  Recall:     {recall:.4f}  (of actual bots, how many did we catch)")
    print(f"  F1 Score:   {f1:.4f}")
    print(f"  Accuracy:   {accuracy:.4f}")
    print(f"  FP Rate:    {fp}/{fp+tn} = {fp/(fp+tn)*100:.1f}%" if (fp+tn) > 0 else "")
    print(f"  FN Rate:    {fn}/{fn+tp} = {fn/(fn+tp)*100:.1f}%" if (fn+tp) > 0 else "")

    # Score distribution
    print(f"\n\n  {'═' * 70}")
    print(f"  📊 SCORE DISTRIBUTION")
    print(f"  {'═' * 70}")

    if drission_results:
        dr_scores_sorted = sorted(dr_scores)
        print(f"\n  DrissionPage scores (n={len(dr_scores_sorted)}):")
        print(f"    P10:    {dr_scores_sorted[int(len(dr_scores_sorted)*0.1)]:.4f}")
        print(f"    P25:    {dr_scores_sorted[int(len(dr_scores_sorted)*0.25)]:.4f}")
        print(f"    Median: {dr_scores_sorted[int(len(dr_scores_sorted)*0.5)]:.4f}")
        print(f"    P75:    {dr_scores_sorted[int(len(dr_scores_sorted)*0.75)]:.4f}")
        print(f"    P90:    {dr_scores_sorted[int(len(dr_scores_sorted)*0.9)]:.4f}")

    if human_results:
        h_scores_sorted = sorted(h_scores)
        print(f"\n  Human scores (n={len(h_scores_sorted)}):")
        print(f"    P10:    {h_scores_sorted[int(len(h_scores_sorted)*0.1)]:.4f}")
        print(f"    P25:    {h_scores_sorted[int(len(h_scores_sorted)*0.25)]:.4f}")
        print(f"    Median: {h_scores_sorted[int(len(h_scores_sorted)*0.5)]:.4f}")
        print(f"    P75:    {h_scores_sorted[int(len(h_scores_sorted)*0.75)]:.4f}")
        print(f"    P90:    {h_scores_sorted[int(len(h_scores_sorted)*0.9)]:.4f}")

    # Histogram (ASCII)
    print(f"\n  Score Histogram:")
    print(f"  {'Score Range':<15} {'DrissionPage':>12} {'Human':>8}")
    print(f"  {'─' * 40}")
    bins = [(0, 0.1), (0.1, 0.2), (0.2, 0.3), (0.3, 0.4), (0.4, 0.5),
            (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01)]
    for lo, hi in bins:
        dr_count = sum(1 for s in dr_scores if lo <= s < hi) if drission_results else 0
        h_count = sum(1 for s in h_scores if lo <= s < hi) if human_results else 0
        dr_bar = "█" * dr_count
        h_bar = "░" * h_count
        print(f"  {lo:.1f} - {hi:.1f}    {dr_count:>4} {dr_bar}")
        if h_count:
            print(f"  {'(human)':>14} {h_count:>4} {h_bar}")


    # Top signals that catch DrissionPage
    print(f"\n\n  {'═' * 70}")
    print(f"  🎯 TOP SIGNALS CATCHING DrissionPage")
    print(f"  {'═' * 70}")

    signal_scores = {}
    for r in drission_results:
        for sig in r.get("signals", []):
            name = sig.get("signalName", "unknown")
            if name not in signal_scores:
                signal_scores[name] = []
            signal_scores[name].append(sig.get("score", 0))

    if signal_scores:
        print(f"\n  {'Signal':<25} {'Avg Score':>10} {'Fires>0.5':>10} {'Max':>7}")
        print(f"  {'─' * 55}")
        for name in sorted(signal_scores.keys(),
                          key=lambda n: statistics.mean(signal_scores[n]),
                          reverse=True):
            scores = signal_scores[name]
            avg = statistics.mean(scores)
            fires = sum(1 for s in scores if s > 0.5)
            mx = max(scores)
            bar = "█" * int(avg * 20)
            print(f"  {name:<25} {avg:>10.4f} {fires:>7}/{len(scores):<3} {mx:>7.4f} {bar}")

    # Missed bots analysis
    missed = [r for r in drission_results if not r["detected"]]
    if missed:
        print(f"\n\n  {'═' * 70}")
        print(f"  ⚠️  MISSED DrissionPage BOTS ({len(missed)}/{len(drission_results)})")
        print(f"  {'═' * 70}")
        for r in sorted(missed, key=lambda x: x["score"], reverse=True)[:10]:
            print(f"\n  {r['sessionId']} ({r['type']}) — score: {r['score']:.4f}")
            top_sigs = sorted(r.get("signals", []),
                            key=lambda s: s.get("score", 0), reverse=True)[:3]
            for s in top_sigs:
                print(f"    {s.get('signalName','?'):<22} {s.get('score',0):.3f}")

    # False positives analysis
    false_pos = [r for r in human_results if r["detected"]]
    if false_pos:
        print(f"\n\n  {'═' * 70}")
        print(f"  ⚠️  FALSE POSITIVES ({len(false_pos)}/{len(human_results)} humans flagged)")
        print(f"  {'═' * 70}")
        for r in sorted(false_pos, key=lambda x: x["score"], reverse=True)[:5]:
            print(f"\n  {r['sessionId']} — score: {r['score']:.4f}")
            top_sigs = sorted(r.get("signals", []),
                            key=lambda s: s.get("score", 0), reverse=True)[:3]
            for s in top_sigs:
                print(f"    {s.get('signalName','?'):<22} {s.get('score',0):.3f}")

    print(f"\n{'=' * 70}")

    # Save full results
    output = {
        "test_info": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_sessions": len(sessions),
            "valid_results": len(valid_results),
            "errors": errors,
            "elapsed_seconds": elapsed,
        },
        "overall_metrics": {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "accuracy": accuracy,
            "tp": tp, "fn": fn, "tn": tn, "fp": fp,
        },
        "by_type": {t: {
            "count": s["count"],
            "caught": s["caught"],
            "detection_rate": s["rate"],
            "avg_score": s["avg_score"],
            "min_score": s["min_score"],
            "max_score": s["max_score"],
            "std_score": s["std_score"],
        } for t, s in type_stats.items()},
        "results": results,
    }

    output_path = os.path.join(OUTPUT_DIR, "drission_deep_test.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"  💾 Full results saved to {output_path}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
