# 🎬 Live Demo Flow — Bots → Dashboard → You

A 3-minute live flow for the judges. Memorize the order, not the words.

## 0. Pre-flight (do this BEFORE you walk on stage)

Open three terminals and start them in this order:

```
# Terminal 1 — API
cd AISecutity/AISecutity
dotnet run --urls http://localhost:5000

# Terminal 2 — ML service
python ml/ml_service.py

# Terminal 3 — Customer site
cd customer-demo-site
python -m http.server 8080
```

Open these tabs in your browser:
1. `http://localhost:8080/`              ← ShopMax storefront
2. `http://localhost:8080/dashboard.html` ← The detection dashboard
3. A 4th terminal you'll run the attack from

## 1. Launch the bot attack (≈30s)

In the 4th terminal:
```
python demo/run_attack.py
```

While it runs, narrate:
> "I'm sending 15 different bots — scrapers, brute-forcers, headless Chrome, Playwright, Selenium, residential-proxy bots — each with different timing, mouse, and request patterns."

You'll see live output like:
```
Speed Scraper          score= 0.94   🚨 CAUGHT
Slow Crawler           score= 0.81   🚨 CAUGHT
Brute Force            score= 0.97   🚨 CAUGHT
...
Caught: 15/15   Errors: 0
```

## 2. Show the dashboard (≈60s)

Switch to the dashboard tab. Refresh once.

Point at, in order:
- **The pie / bar chart** — "15 sessions, all flagged red."
- **The table rows** — "Each bot, its score, its IP, its bot-type label."
- **Click one row** — "Here's why we caught it: timing jitter 0.02, mouse jerk flat, no sec-ch-ua headers, UA is python-requests."

> "Zero false positives so far."

## 3. Browse the site yourself (≈60s)

Switch to the ShopMax tab. Do **real human stuff** for ~20 seconds:
- Hover around, move the mouse in curves
- Click a product
- Scroll a bit
- Use the search box, type something, delete it, retype
- Go back, click another product

Switch back to the dashboard, refresh once.

> "And here's me. Same system, same signals — but I show up green, low score. The model can tell the difference in real time."

## 4. The wrap (≈20s)

> "One script tag on the customer's site. Bots get banned or tarpitted, humans get a clean experience, and the operator sees everything in this dashboard."

## If something goes sideways

| Problem | Fix |
|---|---|
| `run_attack.py` errors immediately | Check terminal 1 — API isn't up. Re-run `dotnet run`. |
| All bots show ⚠️ MISSED | The ML service (terminal 2) probably isn't up. |
| Your own session doesn't appear | Browse for 10+ seconds and refresh the dashboard. |
| Dashboard is empty | Hard refresh (Ctrl+F5). |
