# Customer Demo Site — ShopMax

This is a sample e-commerce website that demonstrates how to integrate AISecutity bot detection.

## Quick Start

### Step 1: Start the AISecutity backend
```bash
cd AISecutity/AISecutity
dotnet run --urls http://localhost:5000
```

### Step 2: Start the ML service (optional, for better detection)
```bash
python ml/ml_service.py
```

### Step 3: Open the demo site
```bash
cd customer-demo-site
python -m http.server 8080
```

Then open: **http://localhost:8080**

### Step 4: Browse the site
- Click products, scroll through blog posts, type in the search bar
- The AISecutity tracker is recording your activity automatically
- Check the console — you'll see `[AISecutity] Tracker initialized`

### Step 5: View the dashboard
Open: **http://localhost:8080/dashboard.html**

You'll see:
- Total sessions
- Bots detected vs humans verified
- Live session feed with scores
- Per-session action (allow/monitor/challenge/block)

---

## How Integration Works

### For any website — just add ONE script tag:

```html
<script src="http://localhost:5000/sdk/tracker.js" 
        data-api-key="YOUR_API_KEY"
        data-endpoint="http://localhost:5000/api/sdk/track">
</script>
```

That's it. The script:
1. Tracks mouse movements, clicks, scrolls, keyboard
2. Batches events every 10 seconds
3. Sends to the AISecutity API
4. API analyzes with 13 detection signals + ML model
5. Returns verdict: allow / monitor / challenge / block

### Dashboard API:
```
GET http://localhost:5000/api/sdk/dashboard?apiKey=YOUR_KEY
```

### Check if a specific IP is banned:
```
GET http://localhost:5000/api/ban/check?ip=1.2.3.4
```

---

## Files

- `index.html` — The demo e-commerce site (with tracker integrated)
- `dashboard.html` — The customer dashboard (shows detection results)
- `README.md` — This file
