"""
ML Bot Detector — Predict on new sessions.

Load the trained model and classify new sessions as bot or human.
Can be used as a standalone script or imported as a module.

Usage:
    python ml/predict.py <session_file.json>
    python ml/predict.py  (uses challenge bot data by default)
"""

import json
import os
import pickle
import sys
from datetime import datetime

import numpy as np


def load_model(model_path="./ml/output/bot_detector_model.pkl"):
    """Load the trained model."""
    with open(model_path, "rb") as f:
        data = pickle.load(f)
    return data["model"], data["feature_names"]


def extract_features(session: dict) -> dict:
    """Extract features from a session (same as training)."""
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

    mouse_speeds = [e["mouse"]["speed"] for e in events if e.get("mouse") and e["mouse"].get("speed")]
    if mouse_speeds:
        avg_mouse_speed = np.mean(mouse_speeds)
        std_mouse_speed = np.std(mouse_speeds)
        cv_mouse_speed = std_mouse_speed / avg_mouse_speed if avg_mouse_speed > 0 else 0
        high_speed_ratio = sum(1 for s in mouse_speeds if s > 1000) / len(mouse_speeds)
    else:
        avg_mouse_speed = std_mouse_speed = cv_mouse_speed = high_speed_ratio = 0

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
    else:
        avg_key_delay = avg_error_rate = avg_burst_length = 0

    endpoints = [e["endpoint"] for e in events if e.get("endpoint")]
    api_endpoints = [ep for ep in endpoints if ep.startswith("/api/")]
    api_ratio = len(api_endpoints) / len(endpoints) if endpoints else 0
    unique_ratio = len(set(endpoints)) / len(endpoints) if endpoints else 0
    session_duration = (times[-1] - times[0]).total_seconds()

    pauses = sum(1 for i in intervals if i > 3000)
    pause_ratio = pauses / len(intervals)
    idle_gaps = sum(1 for i in intervals if i > 10000)

    event_types = [e["eventType"] for e in events]
    api_call_ratio = event_types.count("api_call") / len(event_types)
    click_ratio = event_types.count("click") / len(event_types)
    scroll_ratio = event_types.count("scroll") / len(event_types)
    nav_ratio = event_types.count("navigation") / len(event_types)

    return {
        "mean_interval": mean_interval, "std_interval": std_interval,
        "cv_interval": cv_interval, "min_interval": min_interval,
        "max_interval": max_interval, "pct_under_200ms": pct_under_200ms,
        "pct_under_500ms": pct_under_500ms, "avg_mouse_speed": avg_mouse_speed,
        "std_mouse_speed": std_mouse_speed, "cv_mouse_speed": cv_mouse_speed,
        "high_speed_ratio": high_speed_ratio, "curve_ratio": curve_ratio,
        "avg_key_delay": avg_key_delay, "avg_error_rate": avg_error_rate,
        "avg_burst_length": avg_burst_length, "api_ratio": api_ratio,
        "unique_ratio": unique_ratio, "session_duration": session_duration,
        "pause_ratio": pause_ratio, "idle_gaps": idle_gaps,
        "api_call_ratio": api_call_ratio, "click_ratio": click_ratio,
        "scroll_ratio": scroll_ratio, "nav_ratio": nav_ratio,
        "num_events": len(events),
    }


def predict_session(model, feature_names, session: dict) -> dict:
    """Predict whether a session is a bot or human."""
    feat = extract_features(session)
    if feat is None:
        return {"error": "Not enough events"}

    X = np.array([[feat[name] for name in feature_names]])
    prob = model.predict_proba(X)[0][1]  # probability of being a bot
    prediction = "bot" if prob >= 0.5 else "human"

    return {
        "sessionId": session.get("sessionId", "unknown"),
        "prediction": prediction,
        "bot_probability": round(float(prob), 4),
        "confidence": round(float(max(prob, 1 - prob)), 4),
        "ground_truth": session.get("label", "unknown"),
    }


def main():
    # Determine input file
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = "./challenge_bot_data/challenge_bot_sessions.json"

    print(f"Loading model...")
    model, feature_names = load_model()

    print(f"Loading sessions from {input_file}...")
    with open(input_file, "r", encoding="utf-8") as f:
        sessions = json.load(f)

    print(f"Predicting {len(sessions)} sessions...\n")

    results = []
    for session in sessions:
        result = predict_session(model, feature_names, session)
        results.append(result)

    # Summary
    bots_detected = sum(1 for r in results if r["prediction"] == "bot")
    humans_detected = sum(1 for r in results if r["prediction"] == "human")

    print(f"Results:")
    print(f"  Detected as bot:   {bots_detected}")
    print(f"  Detected as human: {humans_detected}")

    # Show first 10
    print(f"\nFirst 10 predictions:")
    for r in results[:10]:
        gt = r.get("ground_truth", "?")
        correct = "✓" if (r["prediction"] == "bot" and gt in ("bot", "sneaky_bot", "challenge_bot")) or (r["prediction"] == "human" and gt == "human") else "✗"
        print(f"  {r['sessionId']:30} → {r['prediction']:6} (prob={r['bot_probability']:.3f}) [{correct} actual={gt}]")

    # Save
    output_path = "./ml/output/predictions.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results saved to {output_path}")


if __name__ == "__main__":
    main()
