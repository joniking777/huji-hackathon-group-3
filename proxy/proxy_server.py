"""
AISecutity Proxy v2 — Server-side tracking approach.

Instead of injecting tracker.js and hoping the browser sends telemetry,
the proxy itself reports every page navigation to the API server-side.
This eliminates all CORS / iframe / encoding issues.

Usage:
    python proxy/proxy_server.py
    Open http://localhost:8090

Architecture:
    Browser --> proxy:8090 --> target site
                   |
                   +--> POST to localhost:5000/api/sdk/track (server-side)
                   |
                   +--> split-view with embedded mini-dashboard
"""

import asyncio
import re
import sys
import time
import uuid
from html import escape
from urllib.parse import quote, unquote, urljoin, urlparse

import aiohttp
from aiohttp import web

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROXY_PORT = 8090
API_BASE = "http://localhost:5000"
API_KEY = "shopmax-demo-key"

HEADERS_TO_STRIP = {
    "content-security-policy",
    "content-security-policy-report-only",
    "x-frame-options",
    "x-content-type-options",
    "strict-transport-security",
    "content-encoding",
    "content-length",
    "transfer-encoding",
}

UPSTREAM_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "he,en-US;q=0.9,en;q=0.8",
}

# Tag attributes we rewrite.
URL_ATTRS = {
    "a": ["href"], "link": ["href"], "img": ["src", "data-src"],
    "script": ["src"], "iframe": ["src"], "form": ["action"],
    "source": ["src"], "video": ["src", "poster"], "audio": ["src"],
}

CSS_URL_RE = re.compile(r"""url\(\s*(['"]?)([^'")]+)\1\s*\)""", re.I)

# ---------------------------------------------------------------------------
# Session tracking (server-side)
# ---------------------------------------------------------------------------

# One session per browser tab (tracked via cookie)
sessions = {}  # cookie_id -> { session_id, events[], last_seen }


async def report_event(session_id: str, user_agent: str, url: str, event_type: str):
    """Fire-and-forget: POST an event to the API."""
    payload = {
        "apiKey": API_KEY,
        "sessionId": session_id,
        "userAgent": user_agent,
        "url": url,
        "events": [{
            "sessionId": session_id,
            "userId": API_KEY,
            "timestamp": asyncio.get_event_loop().time().__str__(),
            "eventType": event_type,
            "endpoint": urlparse(url).path or "/",
            "durationMs": 0,
        }],
    }
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(
                f"{API_BASE}/api/sdk/track",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=3),
            )
    except Exception:
        pass


def get_or_create_session(request: web.Request) -> tuple:
    """Get session from cookie or create a new one. Returns (session_id, cookie_id, is_new)."""
    cookie_id = request.cookies.get("_aisec_proxy_sid")
    if cookie_id and cookie_id in sessions:
        sessions[cookie_id]["last_seen"] = time.time()
        return sessions[cookie_id]["session_id"], cookie_id, False

    cookie_id = str(uuid.uuid4())[:16]
    session_id = f"proxy-{int(time.time())}-{cookie_id[:8]}"
    sessions[cookie_id] = {"session_id": session_id, "last_seen": time.time()}
    return session_id, cookie_id, True


# ---------------------------------------------------------------------------
# URL rewriting
# ---------------------------------------------------------------------------

def proxify(target_url: str, kind: str = "browse") -> str:
    return f"/{kind}?url={quote(target_url, safe='')}"


def absolutize(base_url: str, maybe_relative: str) -> str:
    if not maybe_relative:
        return maybe_relative
    s = maybe_relative.strip()
    if s.startswith(("data:", "javascript:", "mailto:", "tel:", "#")):
        return s
    if s.startswith("//"):
        return urlparse(base_url).scheme + ":" + s
    return urljoin(base_url, s)


def rewrite_css(base_url: str, css_text: str) -> str:
    def url_sub(m):
        q, raw = m.group(1), m.group(2)
        if raw.startswith(("data:", "#")):
            return f"url({q}{raw}{q})"
        absu = absolutize(base_url, raw)
        return f"url({q}{proxify(absu, 'asset')}{q})"
    return CSS_URL_RE.sub(url_sub, css_text)


def rewrite_html(html: str, base_url: str) -> str:
    """Rewrite links/assets in HTML to go through the proxy."""

    def attr_sub(match):
        tag = match.group("tag").lower()
        attrs = match.group("attrs")
        attrs_new = attrs

        for attr in URL_ATTRS.get(tag, []):
            pattern = re.compile(
                rf"""(?P<pre>\s{re.escape(attr)}\s*=\s*)(?P<q>['"])(?P<val>[^'"]*)(?P=q)""",
                re.I,
            )

            def one(m):
                val = m.group("val")
                if not val or val.startswith(("data:", "javascript:", "mailto:", "tel:", "#")):
                    return m.group(0)
                absu = absolutize(base_url, val)
                if absu.startswith(("http://", "https://")):
                    kind = "browse" if tag in ("a", "iframe", "form") else "asset"
                    new_val = proxify(absu, kind)
                else:
                    new_val = absu
                return f"{m.group('pre')}{m.group('q')}{new_val}{m.group('q')}"

            attrs_new = pattern.sub(one, attrs_new)
        return f"<{match.group('tag')}{attrs_new}>"

    tag_pattern = re.compile(
        r"""<(?P<tag>a|link|img|script|iframe|form|source|video|audio)(?P<attrs>\s[^>]*)>""",
        re.I,
    )
    html = tag_pattern.sub(attr_sub, html)

    # Rewrite inline <style>
    def style_sub(m):
        return f"<style{m.group(1) or ''}>{rewrite_css(base_url, m.group(2))}</style>"
    html = re.sub(r"<style(\s[^>]*)?>([\s\S]*?)</style>", style_sub, html, flags=re.I)

    # Rewrite style="" attributes
    def inline_style_sub(m):
        return f'{m.group(1)}"{rewrite_css(base_url, m.group(2))}"'
    html = re.sub(r'(\sstyle\s*=\s*)"([^"]*)"', inline_style_sub, html, flags=re.I)

    # Remove CSP meta tags
    html = re.sub(
        r"""<meta[^>]+http-equiv\s*=\s*['"]content-security-policy['"][^>]*>""",
        "", html, flags=re.I,
    )

    return html


# ---------------------------------------------------------------------------
# HTTP handlers
# ---------------------------------------------------------------------------

async def fetch_upstream(session: aiohttp.ClientSession, url: str):
    async with session.get(url, headers=UPSTREAM_HEADERS, allow_redirects=True, timeout=20) as r:
        body = await r.read()
        return r.status, dict(r.headers), str(r.url), body


async def landing(_request: web.Request) -> web.Response:
    return web.Response(text=LANDING_HTML, content_type="text/html", charset="utf-8")


async def browse(request: web.Request) -> web.StreamResponse:
    url = request.query.get("url")
    if not url:
        raise web.HTTPFound("/")
    url = unquote(url)
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Get/create session and report navigation server-side
    session_id, cookie_id, is_new = get_or_create_session(request)
    ua = request.headers.get("User-Agent", "unknown")
    asyncio.ensure_future(report_event(session_id, ua, url, "navigation"))

    try:
        async with aiohttp.ClientSession() as session:
            status, headers, final_url, body = await fetch_upstream(session, url)
    except Exception as e:
        return web.Response(
            text=f"<h1>Proxy fetch failed</h1><pre>{escape(str(e))}</pre><p><a href='/'>Try another</a></p>",
            content_type="text/html", status=502,
        )

    content_type = headers.get("Content-Type", "text/html").lower()
    out_headers = {k: v for k, v in headers.items() if k.lower() not in HEADERS_TO_STRIP}

    if "text/html" in content_type or "application/xhtml" in content_type:
        try:
            html = body.decode("utf-8", errors="replace")
        except Exception:
            html = body.decode("latin-1", errors="replace")
        rewritten = rewrite_html(html, final_url)

        resp = web.Response(
            body=rewritten.encode("utf-8"),
            status=status,
            headers={**out_headers, "Content-Type": "text/html; charset=utf-8"},
        )
    else:
        resp = web.Response(body=body, status=status, headers={**out_headers, "Content-Type": content_type})

    # Set session cookie
    resp.set_cookie("_aisec_proxy_sid", cookie_id, max_age=3600, httponly=True, samesite="Lax")
    return resp


async def asset(request: web.Request) -> web.StreamResponse:
    url = request.query.get("url")
    if not url:
        return web.Response(status=400, text="missing url")
    url = unquote(url)
    if not url.startswith(("http://", "https://")):
        return web.Response(status=400, text="absolute url required")

    try:
        async with aiohttp.ClientSession() as session:
            status, headers, final_url, body = await fetch_upstream(session, url)
    except Exception as e:
        return web.Response(status=502, text=f"asset fetch failed: {e}")

    content_type = headers.get("Content-Type", "application/octet-stream").lower()
    out_headers = {k: v for k, v in headers.items() if k.lower() not in HEADERS_TO_STRIP}

    if "text/css" in content_type:
        try:
            css = body.decode("utf-8", errors="replace")
        except Exception:
            css = body.decode("latin-1", errors="replace")
        rewritten = rewrite_css(final_url, css)
        return web.Response(body=rewritten.encode("utf-8"), status=status,
                            headers={**out_headers, "Content-Type": "text/css; charset=utf-8"})

    return web.Response(body=body, status=status, headers={**out_headers, "Content-Type": content_type})


async def split_view(request: web.Request) -> web.Response:
    url = request.query.get("url")
    if not url:
        raise web.HTTPFound("/")
    url = unquote(url)
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    title = urlparse(url).netloc or url
    html = (SPLIT_HTML
            .replace("__TITLE__", escape(title))
            .replace("__URL__", escape(url, quote=True))
            .replace("__URL_ENC__", quote(url, safe="")))
    return web.Response(text=html, content_type="text/html", charset="utf-8")


# ---------------------------------------------------------------------------
# HTML templates
# ---------------------------------------------------------------------------

LANDING_HTML = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<title>AISecutity Proxy</title>
<style>
  body { font-family: 'Segoe UI', Arial, sans-serif; background: linear-gradient(135deg, #1a1f2e, #2c3e50); color: #ecf0f1; margin: 0; padding: 0; min-height: 100vh; display: flex; flex-direction: column; }
  header { padding: 60px 20px 30px; text-align: center; }
  header h1 { font-size: 36px; margin: 0 0 8px; }
  header p { color: #95a5a6; font-size: 16px; margin: 0; }
  .accent { color: #4ecdc4; }
  main { flex: 1; max-width: 720px; margin: 0 auto; padding: 20px; width: 100%; box-sizing: border-box; }
  form { background: #2c3e50; padding: 30px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); margin-bottom: 20px; }
  label { display: block; margin-bottom: 8px; color: #bdc3c7; font-size: 13px; }
  .row { display: flex; gap: 8px; }
  input[type=text] { flex: 1; padding: 14px 16px; border: 2px solid #34495e; background: #1a1f2e; color: #fff; border-radius: 8px; font-size: 15px; }
  input[type=text]:focus { outline: none; border-color: #4ecdc4; }
  button { padding: 14px 24px; background: #4ecdc4; color: #1a1f2e; border: none; border-radius: 8px; font-size: 15px; font-weight: bold; cursor: pointer; }
  button:hover { background: #3db8af; }
  .quick { margin-top: 16px; display: flex; gap: 8px; flex-wrap: wrap; }
  .quick a { background: #34495e; color: #ecf0f1; padding: 6px 12px; border-radius: 14px; text-decoration: none; font-size: 12px; }
  .quick a:hover { background: #4ecdc4; color: #1a1f2e; }
  .links { display: flex; justify-content: center; gap: 24px; margin-top: 20px; }
  .links a { color: #4ecdc4; text-decoration: none; font-size: 14px; }
  .links a:hover { text-decoration: underline; }
  .note { color: #7f8c8d; font-size: 12px; line-height: 1.6; margin-top: 30px; padding: 16px; background: rgba(0,0,0,0.2); border-right: 3px solid #4ecdc4; border-radius: 4px; }
  footer { text-align: center; padding: 20px; color: #7f8c8d; font-size: 12px; }
</style>
</head>
<body>
<header>
  <h1><span class="accent">AISecutity</span> Proxy</h1>
  <p>Enter a URL. Browse it through us. See the session in the dashboard.</p>
</header>
<main>
  <form action="/split" method="get">
    <label for="url">Target URL</label>
    <div class="row">
      <input id="url" name="url" type="text" placeholder="https://www.example.com" autofocus required>
      <button type="submit">Open Site + Dashboard</button>
    </div>
    <div class="quick">
      <a href="/split?url=https%3A%2F%2Fwww.example.com">example.com</a>
      <a href="/split?url=https%3A%2F%2Fnews.ycombinator.com">Hacker News</a>
      <a href="/split?url=https%3A%2F%2Fen.wikipedia.org%2Fwiki%2FMain_Page">Wikipedia</a>
      <a href="/split?url=http%3A%2F%2Flocalhost%3A8080">ShopMax (local)</a>
    </div>
  </form>
  <div class="links">
    <a href="http://localhost:8080/dashboard.html" target="_blank">Full Dashboard</a>
    <a href="http://localhost:8080/compare.html" target="_blank">Compare View</a>
  </div>
  <div class="note">
    <strong>How it works:</strong> Every page you visit through this proxy is reported
    server-side to the AISecutity API. No client-side JS injection needed.
    Your browsing session appears in the dashboard in real-time.
  </div>
</main>
<footer>AISecutity Hackathon Demo | proxy :8090 | API :5000</footer>
</body>
</html>
"""

SPLIT_HTML = """<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
<meta charset="utf-8">
<title>AISecutity - __TITLE__</title>
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; height: 100%; font-family: 'Segoe UI', Arial, sans-serif; background: #0d1117; color: #ecf0f1; overflow: hidden; }
  .topbar { display: flex; align-items: center; gap: 12px; background: #1a1f2e; padding: 10px 16px; border-bottom: 2px solid #4ecdc4; height: 52px; }
  .topbar .logo { font-weight: 700; color: #4ecdc4; font-size: 14px; }
  .topbar form { flex: 1; display: flex; gap: 6px; }
  .topbar input { flex: 1; padding: 8px 12px; border: 1px solid #34495e; background: #0d1117; color: #fff; border-radius: 6px; font-size: 13px; }
  .topbar button { padding: 8px 14px; background: #4ecdc4; color: #1a1f2e; border: none; border-radius: 6px; font-weight: 600; cursor: pointer; font-size: 13px; }
  .topbar a { color: #95a5a6; text-decoration: none; font-size: 12px; white-space: nowrap; }
  .topbar a:hover { color: #fff; }
  .body { display: flex; height: calc(100vh - 52px); }
  .pane-site { flex: 1; min-width: 0; background: #fff; }
  .pane-site iframe { width: 100%; height: 100%; border: 0; display: block; }
  .pane-dash { width: 380px; background: #0d1117; padding: 14px; overflow-y: auto; border-right: 2px solid #1a1f2e; }
  .pane-dash h2 { margin: 0 0 10px; color: #4ecdc4; font-size: 14px; letter-spacing: 1px; }
  .stats { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 14px; }
  .stat { background: #1a1f2e; padding: 10px; border-radius: 8px; border-right: 3px solid #4ecdc4; }
  .stat .v { font-size: 22px; font-weight: 700; }
  .stat .l { font-size: 10px; color: #95a5a6; text-transform: uppercase; }
  .stat.bots { border-right-color: #e74c3c; } .stat.bots .v { color: #e74c3c; }
  .stat.humans { border-right-color: #2ecc71; } .stat.humans .v { color: #2ecc71; }
  .stat.pending { border-right-color: #f39c12; } .stat.pending .v { color: #f39c12; }
  .session-list { display: flex; flex-direction: column; gap: 6px; }
  .session { background: #1a1f2e; border-radius: 8px; padding: 10px; border-left: 3px solid #34495e; }
  .session.bot { border-left-color: #e74c3c; }
  .session.human { border-left-color: #2ecc71; }
  .session.pending { border-left-color: #f39c12; }
  .session .row1 { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px; }
  .session .label { font-weight: 700; }
  .session .label.bot { color: #e74c3c; }
  .session .label.human { color: #2ecc71; }
  .session .label.pending { color: #f39c12; }
  .session .pct { font-family: monospace; font-size: 11px; color: #95a5a6; }
  .session .ua { font-size: 10px; color: #7f8c8d; word-break: break-all; }
  .empty { color: #7f8c8d; font-size: 12px; text-align: center; padding: 30px 10px; }
  .pulse { width: 8px; height: 8px; background: #2ecc71; border-radius: 50%; display: inline-block; animation: pulse 1.4s infinite; margin-left: 6px; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
</style>
</head>
<body>
<div class="topbar">
  <span class="logo">AISecutity</span>
  <form action="/split" method="get">
    <input name="url" type="text" value="__URL__" required>
    <button type="submit">Go</button>
  </form>
  <a href="/">New URL</a>
  <a href="http://localhost:8080/dashboard.html" target="_blank">Full Dashboard</a>
</div>
<div class="body">
  <div class="pane-site">
    <iframe id="site" src="/browse?url=__URL_ENC__"></iframe>
  </div>
  <div class="pane-dash">
    <h2>LIVE DETECTIONS <span class="pulse"></span></h2>
    <div class="stats">
      <div class="stat"><div class="v" id="s-total">0</div><div class="l">Total</div></div>
      <div class="stat bots"><div class="v" id="s-bots">0</div><div class="l">Bots</div></div>
      <div class="stat humans"><div class="v" id="s-humans">0</div><div class="l">Humans</div></div>
      <div class="stat pending"><div class="v" id="s-pending">0</div><div class="l">Pending</div></div>
    </div>
    <div class="session-list" id="sessions"><div class="empty">Browse the site on the left. Sessions appear here automatically.</div></div>
  </div>
</div>
<script>
  const API_BASE = 'http://localhost:5000';
  const API_KEY  = 'shopmax-demo-key';

  async function refresh() {
    try {
      const r = await fetch(API_BASE + '/api/sdk/dashboard?apiKey=' + API_KEY);
      if (!r.ok) return;
      const data = await r.json();
      const s = data.summary || {};
      document.getElementById('s-total').textContent   = s.totalSessions   || 0;
      document.getElementById('s-bots').textContent    = s.botsDetected    || 0;
      document.getElementById('s-humans').textContent  = s.humansVerified  || 0;
      document.getElementById('s-pending').textContent = s.pendingAnalysis || 0;

      const list = document.getElementById('sessions');
      const sessions = (data.sessions || []).slice(0, 30);
      if (sessions.length === 0) {
        list.innerHTML = '<div class="empty">Browse the site on the left. Sessions appear here automatically.</div>';
        return;
      }
      list.innerHTML = sessions.map(function(sess) {
        var isBot = sess.isBot;
        var isPending = !isBot && sess.eventCount < 5;
        var cls   = isBot ? 'bot' : (isPending ? 'pending' : 'human');
        var label = isBot ? 'BOT' : (isPending ? 'ANALYZING...' : 'HUMAN');
        var ua    = (sess.userAgent || '').substring(0, 60);
        var score = Math.round((sess.lastScore || 0) * 100) + '%';
        return '<div class="session ' + cls + '">' +
          '<div class="row1"><span class="label ' + cls + '">' + label + '</span>' +
          '<span class="pct">' + score + ' | ' + sess.eventCount + ' events</span></div>' +
          '<div class="ua">' + ua + '</div></div>';
      }).join('');
    } catch (e) {}
  }

  refresh();
  setInterval(refresh, 2000);
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

def build_app() -> web.Application:
    app = web.Application(client_max_size=50 * 1024 * 1024)
    app.router.add_get("/", landing)
    app.router.add_get("/split", split_view)
    app.router.add_get("/browse", browse)
    app.router.add_get("/asset", asset)
    return app


def main():
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    app = build_app()
    print()
    print("=" * 60)
    print("  AISecutity Proxy (server-side tracking)")
    print(f"     Open:        http://localhost:{PROXY_PORT}")
    print(f"     Dashboard:   http://localhost:8080/dashboard.html")
    print(f"     API:         {API_BASE}")
    print("=" * 60)
    print()
    web.run_app(app, host="0.0.0.0", port=PROXY_PORT, print=lambda *_: None)


if __name__ == "__main__":
    main()
