"""
ML Bot Detection Microservice.

Runs as a lightweight HTTP server on port 5050.
The C# API can call this for a second opinion on suspicious sessions.

Endpoints:
  POST /predict  — predict if a session is bot or human
  GET  /health   — health check
"""

import json
import os
import pickle
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

import numpy as np

# Load model on startup
MODEL_PATH = "./ml/output/bot_detector_v2.pkl"

print(f"Loading model from {MODEL_PATH}...")
with open(MODEL_PATH, "rb") as f:
    model_data = pickle.load(f)
    MODEL = model_data["model"]
    FEATURE_NAMES = model_data["feature_names"]
print(f"Model loaded. Features: {len(FEATURE_NAMES)}")


def extract_features(session: dict) -> dict:
    """Extract features from a session."""
    events = session.get("events", [])
    if len(events) < 2:
        return None

    times = []
    for e in events:
        ts = e["timestamp"].replace("Z", "+00:00")
        times.append(datetime.fromisoformat(ts))

    intervals = [(times[i] - times[i-1]).total_seconds() * 1000 for i in range(1, len(times))]

    mean_interval = np.mean(intervals)
    std_interval = np.std(intervals)
    cv_interval = std_interval / mean_interval if mean_interval > 0 else 0
    min_interval = np.min(intervals)
    max_interval = np.max(intervals)
    pct_under_200ms = sum(1 for i in intervals if i < 200) / len(intervals)
    pct_under_500ms = sum(1 for i in intervals if i < 500) / len(intervals)

    median_interval = np.median(intervals)
    skew_ratio = (mean_interval - median_interval) / std_interval if std_interval > 0 else 0

    mouse_speeds = [e["mouse"]["speed"] for e in events if e.get("mouse") and e["mouse"].get("speed")]
    if mouse_speeds:
        avg_mouse_speed = np.mean(mouse_speeds)
        std_mouse_speed = np.std(mouse_speeds)
        cv_mouse_speed = std_mouse_speed / avg_mouse_speed if avg_mouse_speed > 0 else 0
        high_speed_ratio = sum(1 for s in mouse_speeds if s > 1000) / len(mouse_speeds)
        max_mouse_speed = np.max(mouse_speeds)
    else:
        avg_mouse_speed = std_mouse_speed = cv_mouse_speed = high_speed_ratio = max_mouse_speed = 0

    mouse_events = [e for e in events if e.get("mouse")]
    curve_ratio = sum(1 for e in mouse_events if e["mouse"].get("hasCurve")) / len(mouse_events) if mouse_events else 0.5

    key_events = [e for e in events if e.get("keyboard")]
    if key_events:
        delays = [e["keyboard"]["interKeyDelayMs"] for e in key_events if e["keyboard"].get("interKeyDelayMs")]
        errors = [e["keyboard"]["errorRate"] for e in key_events if e["keyboard"].get("errorRate") is not None]
        bursts = [e["keyboard"]["burstLength"] for e in key_events if e["keyboard"].get("burstLength")]
        avg_key_delay = np.mean(delays) if delays else 0
        avg_error_rate = np.mean(errors) if errors else 0
        avg_burst_length = np.mean(bursts) if bursts else 0
        max_error_rate = np.max(errors) if errors else 0
    else:
        avg_key_delay = avg_error_rate = avg_burst_length = max_error_rate = 0

    endpoints = [e["endpoint"] for e in events if e.get("endpoint")]
    api_ratio = sum(1 for ep in endpoints if ep.startswith("/api/")) / len(endpoints) if endpoints else 0
    unique_ratio = len(set(endpoints)) / len(endpoints) if endpoints else 0

    revisits = sum(1 for i in range(1, len(endpoints)) if endpoints[i] == endpoints[i-1])
    revisit_ratio = revisits / len(endpoints) if endpoints else 0

    session_duration = (times[-1] - times[0]).total_seconds()

    pauses = sum(1 for i in intervals if i > 3000)
    pause_ratio = pauses / len(intervals)
    idle_gaps = sum(1 for i in intervals if i > 10000)

    event_types = [e["eventType"] for e in events]
    click_ratio = event_types.count("click") / len(event_types)
    scroll_ratio = event_types.count("scroll") / len(event_types)

    return {
        "mean_interval": mean_interval, "std_interval": std_interval,
        "cv_interval": cv_interval, "min_interval": min_interval,
        "max_interval": max_interval, "pct_under_200ms": pct_under_200ms,
        "pct_under_500ms": pct_under_500ms, "skew_ratio": skew_ratio,
        "avg_mouse_speed": avg_mouse_speed, "std_mouse_speed": std_mouse_speed,
        "cv_mouse_speed": cv_mouse_speed, "high_speed_ratio": high_speed_ratio,
        "max_mouse_speed": max_mouse_speed, "curve_ratio": curve_ratio,
        "avg_key_delay": avg_key_delay, "avg_error_rate": avg_error_rate,
        "max_error_rate": max_error_rate, "avg_burst_length": avg_burst_length,
        "api_ratio": api_ratio, "unique_ratio": unique_ratio,
        "revisit_ratio": revisit_ratio, "session_duration": session_duration,
        "pause_ratio": pause_ratio, "idle_gaps": idle_gaps,
        "click_ratio": click_ratio, "scroll_ratio": scroll_ratio,
        "num_events": len(events),
    }


class MLHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/predict":
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            session = json.loads(body)

            features = extract_features(session)
            if features is None:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Not enough events"}).encode())
                return

            X = np.array([[features.get(name, 0) for name in FEATURE_NAMES]])
            prob = float(MODEL.predict_proba(X)[0][1])
            prediction = "bot" if prob >= 0.5 else "human"

            result = {
                "prediction": prediction,
                "botProbability": round(prob, 4),
                "confidence": round(max(prob, 1 - prob), 4),
                "modelVersion": "2.0",
                "featuresUsed": len(FEATURE_NAMES),
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "model": "v2.0"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        print(f"  [ML] {args[0]}")


if __name__ == "__main__":
    port = 5050
    server = HTTPServer(("0.0.0.0", port), MLHandler)
    print(f"\n  ML Service running on http://localhost:{port}")
    print(f"  Endpoints:")
    print(f"    POST /predict  — classify a session")
    print(f"    GET  /health   — health check\n")
    server.serve_forever()
