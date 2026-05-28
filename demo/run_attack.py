"""
Demo script — sends 15 different bot types to the AISecutity API.

Run this LIVE during the presentation. Right after it finishes,
switch to the dashboard tab to show the judges the detections,
then browse the customer site yourself to show human detection.

Usage:
    python demo/run_attack.py

Make sure these are running first:
    - AISecutity API:   cd AISecutity/AISecutity && dotnet run --urls http://localhost:5000
    - ML Service:       python ml/ml_service.py
    - Customer Site:    cd customer-demo-site && python -m http.server 8080
"""

import random
import time
from datetime import datetime, timedelta, timezone

import requests

SDK_URL = "http://localhost:5000/api/sdk/track"
DETECT_URL = "http://localhost:5000/api/ban/analyze-and-ban"
API_KEY = "shopmax-demo-key"
SITE_URL = "http://localhost:8080"


def ts(base, offset_ms):
    return (base + timedelta(milliseconds=offset_ms)).isoformat()


def gen_events(base, intervals, event_type, endpoint, mouse_speed, has_curve):
    events = []
    offset = 0
    for i, interval in enumerate(intervals):
        offset += interval
        evt = {
            "timestamp": ts(base, offset),
            "eventType": event_type if isinstance(event_type, str) else event_type[i % len(event_type)],
            "endpoint": endpoint if isinstance(endpoint, str) else endpoint[i % len(endpoint)],
            "durationMs": random.randint(50, 500),
        }
        if mouse_speed > 0:
            evt["mouse"] = {
                "x": random.randint(100, 1800),
                "y": random.randint(100, 900),
                "speed": mouse_speed + random.uniform(-50, 50),
                "hasCurve": has_curve,
            }
        events.append(evt)
    return events


def send_bot(name, label, events, ua):
    """Push the bot session into both the dashboard and the detection engine."""
    session_id = f"{name}-{int(time.time() * 1000)}"
    full_events = [{"sessionId": session_id, "userId": name, **e} for e in events]
    ip = f"10.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 254)}"

    # 1) Register in customer dashboard so judges can see it live
    try:
        requests.post(
            SDK_URL,
            json={
                "apiKey": API_KEY,
                "sessionId": session_id,
                "userAgent": ua,
                "url": SITE_URL,
                "events": full_events,
            },
            timeout=5,
        )
    except Exception:
        pass

    # 2) Run detection so the engine bans / scores it
    try:
        resp = requests.post(
            DETECT_URL,
            json={
                "sessionId": session_id,
                "userId": name,
                "userAgent": ua,
                "ipAddress": ip,
                "events": full_events,
            },
            params={"ipAddress": ip},
            timeout=10,
        )
        if resp.status_code == 200:
            r = resp.json()
            return r.get("detected", False), r.get("aiProbabilityScore", 0.0)
    except Exception:
        pass
    return None, 0.0


def main():
    print("=" * 64)
    print("  🤖 BOT ATTACK SIMULATION — AISecutity")
    print("  Sending 15 different bots against ShopMax")
    print(f"  Dashboard:  {SITE_URL}/dashboard.html")
    print(f"  Compare:    {SITE_URL}/compare.html")
    print("=" * 64)
    print()

    base = datetime.now(timezone.utc)

    bots = [
        ("speed-scraper", "Speed Scraper", gen_events(
            base, [random.uniform(50, 150) for _ in range(15)],
            ["api_call", "navigation"], ["/api/products", "/api/prices", "/products/1"],
            5000, False), "python-requests/2.31.0"),

        ("slow-crawler", "Slow Crawler", gen_events(
            base, [random.uniform(2000, 3000) for _ in range(12)],
            "navigation", [f"/products/{i}" for i in range(1, 13)],
            800, True), "Mozilla/5.0 (compatible; Googlebot/2.1)"),

        ("brute-forcer", "Brute Force", gen_events(
            base, [random.uniform(200, 500) for _ in range(20)],
            ["navigation", "keypress", "form_submit", "navigation"],
            ["/login", "/login", "/login", "/login"],
            4000, False), "Mozilla/5.0 (Windows NT 10.0) Chrome/125.0"),

        ("content-scraper", "Content Scraper", gen_events(
            base, [random.uniform(800, 1200) for _ in range(18)],
            ["navigation", "scroll", "scroll", "scroll"],
            ["/blog/post-1", "/blog/post-1", "/blog/post-1", "/blog/post-2"],
            600, False), "Scrapy/2.11.0"),

        ("price-monitor", "Price Monitor", gen_events(
            base, [random.uniform(100, 300) for _ in range(10)],
            "api_call", ["/api/products/1", "/api/products/2", "/api/products/3"],
            0, False), "PriceBot/1.0"),

        ("seo-crawler", "SEO Crawler", gen_events(
            base, [random.uniform(1500, 2500) for _ in range(14)],
            "navigation", ["/", "/products", "/about", "/blog", "/contact", "/faq"],
            900, True), "Mozilla/5.0 (compatible; AhrefsBot/7.0)"),

        ("account-checker", "Account Checker", gen_events(
            base, [random.uniform(300, 700) for _ in range(16)],
            ["navigation", "keypress", "form_submit", "navigation"],
            ["/login", "/login", "/api/auth/check", "/account"],
            3500, False), "Mozilla/5.0 (Linux; Android 14) Chrome/125.0"),

        ("image-scraper", "Image Scraper", gen_events(
            base, [random.uniform(100, 400) for _ in range(12)],
            "navigation", ["/products/1/image", "/products/2/image", "/products/3/image"],
            0, False), "curl/8.4.0"),

        ("headless-chrome", "Headless Chrome", gen_events(
            base, [random.gauss(6000, 150) for _ in range(8)],
            "navigation", ["/", "/products", "/about", "/contact", "/blog"],
            1200, False), "Mozilla/5.0 (Windows NT 10.0) HeadlessChrome/148.0"),

        ("playwright-bot", "Playwright", gen_events(
            base, [random.uniform(1000, 2000) for _ in range(10)],
            ["click", "navigation", "scroll"],
            ["/products", "/products/3", "/products/3", "/cart"],
            1100, True), "Mozilla/5.0 (Windows NT 10.0) Chrome/125.0"),

        ("selenium-bot", "Selenium", gen_events(
            base, [random.gauss(3000, 300) for _ in range(11)],
            ["navigation", "click", "click"],
            ["/", "/products", "/products/5", "/cart", "/checkout"],
            950, False), "Mozilla/5.0 (Windows NT 10.0) Chrome/125.0"),

        ("data-harvester", "Data Harvester", gen_events(
            base, [random.uniform(500, 1000) for _ in range(15)],
            ["navigation", "scroll", "scroll", "navigation"],
            ["/products", "/products", "/products", "/products/1"],
            700, False), "Mozilla/5.0 (Macintosh) Safari/605.1"),

        ("residential-bot", "Residential Proxy", gen_events(
            base, [random.lognormvariate(7.0, 0.4) for _ in range(9)],
            "navigation", ["/", "/products", "/products/2", "/products/5", "/cart"],
            750, True), "Mozilla/5.0 (iPhone) Safari/605.1"),

        ("api-abuser", "API Abuser", gen_events(
            base, [random.uniform(30, 80) for _ in range(25)],
            "api_call", ["/api/products", "/api/search", "/api/cart/add"],
            0, False), "Go-http-client/2.0"),

        ("click-farm", "Click Farm", gen_events(
            base, [random.uniform(2000, 4000) for _ in range(10)],
            "click", ["/products/1", "/products/2", "/products/3", "/products/4"],
            1000, True), "Mozilla/5.0 (Windows NT 10.0) Firefox/126.0"),
    ]

    results = []
    for name, label, events, ua in bots:
        detected, score = send_bot(name, label, events, ua)
        if detected is None:
            tag = "❌ ERROR"
        elif detected:
            tag = "🚨 CAUGHT"
        else:
            tag = "⚠️  MISSED"
        print(f"  {label:<22} score={score:>6.3f}   {tag}")
        results.append({"label": label, "detected": detected, "score": score})
        time.sleep(0.2)

    caught = sum(1 for r in results if r["detected"])
    errors = sum(1 for r in results if r["detected"] is None)
    print()
    print("  " + "─" * 50)
    print(f"  Caught: {caught}/15   Errors: {errors}")
    print()
    print("  ➡  Show the judges:")
    print(f"     1. Dashboard:   {SITE_URL}/dashboard.html")
    print(f"     2. Compare:     {SITE_URL}/compare.html")
    print(f"     3. Browse {SITE_URL}/ yourself — you'll show up as 🟢 HUMAN")
    print("=" * 64)


if __name__ == "__main__":
    main()
