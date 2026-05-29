"""Export presentation to PDF using Chrome DevTools Protocol."""
import base64
import json
import os
import subprocess
import tempfile
import time
import socket
import urllib.request

HTML_PATH = os.path.abspath("presentation (1).html")
OUTPUT_PDF = os.path.abspath("presentation.pdf")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# Create modified HTML showing all slides with print-friendly settings
with open(HTML_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# Force backgrounds to print + show all slides + landscape
inject_css = """
<style>
* { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
@page { size: A4 landscape; margin: 0; }
body { overflow: visible !important; height: auto !important; display: block !important; }
.slide {
    display: flex !important;
    position: relative !important;
    page-break-after: always;
    break-after: page;
    height: 100vh;
    min-height: 700px;
    box-sizing: border-box;
}
.btn-container { display: none !important; }
.footer-note { display: none !important; }
</style>
<script>
window.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.slide').forEach(s => s.classList.add('active'));
});
</script>
"""
html = html.replace("</head>", inject_css + "\n</head>")

temp_html = os.path.join(tempfile.gettempdir(), "pres_export.html")
with open(temp_html, "w", encoding="utf-8") as f:
    f.write(html)

file_url = "file:///" + temp_html.replace("\\", "/")

# Find a free port for Chrome DevTools
def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

port = find_free_port()
print(f"  Starting Chrome on debug port {port}...")

# Start Chrome with remote debugging
user_data = os.path.join(tempfile.gettempdir(), "chrome_pdf_profile")
chrome_proc = subprocess.Popen([
    CHROME,
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--remote-allow-origins=*",
    f"--remote-debugging-port={port}",
    f"--user-data-dir={user_data}",
    file_url,
], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Wait for Chrome to start
time.sleep(3)

try:
    # Get WebSocket URL from Chrome DevTools — use page target, not browser
    resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/json")
    tabs = json.loads(resp.read())
    # Find the page target (not service worker or other)
    page_tab = next((t for t in tabs if t.get("type") == "page"), tabs[0])
    ws_url = page_tab["webSocketDebuggerUrl"]
    print(f"  Connected to Chrome DevTools (tab: {page_tab.get('title', 'unknown')[:40]})")

    # Connect via WebSocket
    import websocket
    ws = websocket.create_connection(ws_url)

    # Wait for page to fully render
    time.sleep(2)

    # Enable Page domain
    ws.send(json.dumps({"id": 0, "method": "Page.enable", "params": {}}))
    ws.recv()
    time.sleep(1)

    # Print to PDF with backgrounds enabled
    pdf_cmd = {
        "id": 1,
        "method": "Page.printToPDF",
        "params": {
            "landscape": True,
            "printBackground": True,
            "preferCSSPageSize": True,
            "paperWidth": 11.69,
            "paperHeight": 8.27,
            "marginTop": 0,
            "marginBottom": 0,
            "marginLeft": 0,
            "marginRight": 0,
        }
    }
    ws.send(json.dumps(pdf_cmd))
    result = json.loads(ws.recv())

    if "result" in result and "data" in result["result"]:
        pdf_bytes = base64.b64decode(result["result"]["data"])
        with open(OUTPUT_PDF, "wb") as f:
            f.write(pdf_bytes)
        print(f"\n✅ PDF saved: {OUTPUT_PDF}")
        print(f"   Size: {len(pdf_bytes) / 1024:.1f} KB")
        print(f"   Pages: 6 slides (landscape A4)")
    else:
        print(f"\n❌ Error: {result}")

    ws.close()

except Exception as e:
    print(f"\n❌ Error: {e}")
finally:
    chrome_proc.terminate()
    chrome_proc.wait(timeout=5)
    os.remove(temp_html)
