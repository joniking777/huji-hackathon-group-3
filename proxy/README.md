# 🛡️ AISecutity Proxy

A tiny browsing proxy: enter any URL, the user browses through us, the
AISecutity tracker is auto-injected, the session shows up in the dashboard.

## Run it

```bash
# 1. Make sure the API is up
cd AISecutity/AISecutity
dotnet run --urls http://localhost:5000

# 2. Make sure the customer site / dashboard is up
cd customer-demo-site
python -m http.server 8080

# 3. Start the proxy
python proxy/proxy_server.py
```

Then open <http://localhost:8090>, type a URL, click **גלוש דרכנו**.

## What happens

```
You ──▶ http://localhost:8090/browse?url=<target>
                │
                ▼
        proxy_server.py
        ├── fetches the page server-side
        ├── strips CSP / X-Frame-Options
        ├── rewrites <a>, <img>, <script>, CSS url() ... → /asset?url=...
        └── injects <script src=".../sdk/tracker.js">
                │
                ▼
       browser renders proxied page
                │
                ▼
       tracker.js POSTs telemetry to localhost:5000
                │
                ▼
        appears live in /dashboard.html
```

A floating banner is added to every proxied page so you (and the judges)
can see at a glance that the session is being analyzed.

## Honest limitations

This is a hackathon proof-of-concept, not a production man-in-the-middle.

- **CSP & subresource integrity** — we strip the headers, but a few sites
  pin script hashes which then refuse to load.
- **Single-page apps** that hard-code their backend host (or use service
  workers) will break on navigation.
- **Login flows** with cross-origin cookies / OAuth won't survive the trip.
- **POST forms** aren't proxied yet — only GET. (Easy to add, just hasn't
  been needed for the demo.)
- **WebSockets** aren't proxied.

Sites that work well: blogs, news (most of them), wikis, marketing pages,
documentation sites, and our own ShopMax demo.

## Why a proxy at all?

For the demo we want to show:
1. The judges enter `https://news.ycombinator.com` (or anything).
2. They browse it like a normal site.
3. The dashboard fills with **real human telemetry from a real site**, not
   from our toy ShopMax store.

It's the closest we can get to "deploy on a customer site" without
actually deploying anywhere.
