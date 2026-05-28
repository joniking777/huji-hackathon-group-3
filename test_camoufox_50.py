"""Run 50 Camoufox variants to see detection rate."""
import json, random, time, requests
from datetime import datetime, timedelta, timezone

API_URL = "http://localhost:5000/api/ban/analyze-and-ban"

HUMAN_ENDPOINTS = [
    "/home", "/about", "/products", "/products/1", "/products/2",
    "/products/3", "/products/5", "/blog", "/faq", "/contact",
    "/cart", "/products/8", "/products/12",
]

def gen_camoufox(idx):
    base = datetime(2026, 5, 29, 10, 0, 0, tzinfo=timezone.utc)
    events = []
    offset = 0
    num_events = random.randint(8, 20)

    for i in range(num_events):
        # Uniform random timing (Camoufox signature)
        offset += random.uniform(1500, 4500)

        # Bezier-calculated positions
        target_x = 400 + (i * 97 + random.randint(-30, 30)) % 800
        target_y = 250 + (i * 73 + random.randint(-20, 20)) % 500

        distance = ((target_x - (events[-1]["mouse"]["x"] if events else 600))**2 + 
                   (target_y - (events[-1]["mouse"]["y"] if events else 400))**2)**0.5
        move_time = random.uniform(300, 500)
        speed = distance / (move_time / 1000)

        events.append({
            "sessionId": f"camoufox-{idx:03d}",
            "userId": f"cfox-{idx}",
            "timestamp": (base + timedelta(milliseconds=offset)).isoformat(),
            "eventType": random.choice(["click", "navigation", "scroll"]),
            "endpoint": random.choice(HUMAN_ENDPOINTS),
            "durationMs": random.randint(800, 2500),
            "mouse": {"x": target_x, "y": target_y, "speed": round(speed, 1), "hasCurve": True},
        })

        # Sometimes scroll
        if random.random() < 0.3:
            offset += random.uniform(500, 1500)
            events.append({
                "sessionId": f"camoufox-{idx:03d}",
                "userId": f"cfox-{idx}",
                "timestamp": (base + timedelta(milliseconds=offset)).isoformat(),
                "eventType": "scroll",
                "endpoint": events[-1]["endpoint"],
                "durationMs": random.randint(300, 800),
                "mouse": {"x": target_x, "y": target_y + random.randint(100, 300), "speed": round(random.uniform(400, 700), 1), "hasCurve": True},
            })

    return {
        "sessionId": f"camoufox-{idx:03d}",
        "userId": f"cfox-{idx}",
        "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "ipAddress": f"203.0.{random.randint(1,255)}.{random.randint(1,254)}",
        "events": events,
    }

print("=" * 60)
print("  CAMOUFOX STRESS TEST — 50 variants")
print("=" * 60)

results = []
caught = 0
missed = 0

for i in range(50):
    session = gen_camoufox(i)
    try:
        resp = requests.post(API_URL, json=session, params={"ipAddress": session["ipAddress"]}, timeout=10)
        if resp.status_code == 200:
            r = resp.json()
            detected = r.get("detected", False)
            score = r.get("aiProbabilityScore", 0)
            results.append({"idx": i, "detected": detected, "score": score, "events": len(session["events"])})
            if detected:
                caught += 1
            else:
                missed += 1
        else:
            results.append({"idx": i, "detected": None, "score": 0, "error": resp.status_code})
    except Exception as e:
        results.append({"idx": i, "detected": None, "score": 0, "error": str(e)})

    if (i + 1) % 10 == 0:
        print(f"  Processed {i+1}/50...")

# Results
scores = [r["score"] for r in results if r.get("detected") is not None]
detected_scores = [r["score"] for r in results if r.get("detected") == True]
missed_scores = [r["score"] for r in results if r.get("detected") == False]

print(f"\n{'=' * 60}")
print(f"  RESULTS")
print(f"{'=' * 60}")
print(f"\n  Total tested: {len(scores)}")
print(f"  Caught: {caught} ({caught/len(scores)*100:.0f}%)")
print(f"  Missed: {missed} ({missed/len(scores)*100:.0f}%)")
print(f"\n  Score distribution:")
print(f"    Min:  {min(scores):.4f}")
print(f"    Max:  {max(scores):.4f}")
print(f"    Avg:  {sum(scores)/len(scores):.4f}")
if detected_scores:
    print(f"    Avg (caught): {sum(detected_scores)/len(detected_scores):.4f}")
if missed_scores:
    print(f"    Avg (missed): {sum(missed_scores)/len(missed_scores):.4f}")

# Histogram
buckets = {"0-10%": 0, "10-20%": 0, "20-30%": 0, "30-40%": 0, "40-50%": 0, "50-60%": 0, "60%+": 0}
for s in scores:
    pct = s * 100
    if pct < 10: buckets["0-10%"] += 1
    elif pct < 20: buckets["10-20%"] += 1
    elif pct < 30: buckets["20-30%"] += 1
    elif pct < 40: buckets["30-40%"] += 1
    elif pct < 50: buckets["40-50%"] += 1
    elif pct < 60: buckets["50-60%"] += 1
    else: buckets["60%+"] += 1

print(f"\n  Score histogram:")
for bucket, count in buckets.items():
    bar = "█" * count
    print(f"    {bucket:8} {count:3} {bar}")

print(f"\n{'=' * 60}")

with open("camoufox_test_results.json", "w") as f:
    json.dump(results, f, indent=2)
print(f"  Results saved to camoufox_test_results.json")
