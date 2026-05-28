"""
ML Bot Detector v2 — Trained on adversarial data (no /api/ shortcut).

Combines original labeled data + adversarial data where bots never hit /api/.
Forces the model to learn from behavioral signals:
- Timing patterns (CV, distribution shape)
- Mouse dynamics (speed, consistency, curves)
- Keyboard biometrics (delay, errors, bursts)
- Session structure (pauses, revisits, duration)
"""

import json
import os
import pickle
from datetime import datetime

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

OUTPUT_DIR = "./ml/output"


def extract_features(session: dict) -> dict:
    """Extract 24 behavioral features from a session."""
    events = session.get("events", [])
    if len(events) < 2:
        return None

    times = []
    for e in events:
        ts = e["timestamp"].replace("Z", "+00:00")
        times.append(datetime.fromisoformat(ts))

    intervals = [(times[i] - times[i-1]).total_seconds() * 1000 for i in range(1, len(times))]

    # Timing
    mean_interval = np.mean(intervals)
    std_interval = np.std(intervals)
    cv_interval = std_interval / mean_interval if mean_interval > 0 else 0
    min_interval = np.min(intervals)
    max_interval = np.max(intervals)
    pct_under_200ms = sum(1 for i in intervals if i < 200) / len(intervals)
    pct_under_500ms = sum(1 for i in intervals if i < 500) / len(intervals)

    # Timing distribution shape (skewness indicator)
    median_interval = np.median(intervals)
    skew_ratio = (mean_interval - median_interval) / std_interval if std_interval > 0 else 0

    # Mouse
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

    # Keyboard
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

    # Navigation
    endpoints = [e["endpoint"] for e in events if e.get("endpoint")]
    api_ratio = sum(1 for ep in endpoints if ep.startswith("/api/")) / len(endpoints) if endpoints else 0
    unique_ratio = len(set(endpoints)) / len(endpoints) if endpoints else 0

    # Revisit ratio: how often does user go back to same page?
    revisits = sum(1 for i in range(1, len(endpoints)) if endpoints[i] == endpoints[i-1])
    revisit_ratio = revisits / len(endpoints) if endpoints else 0

    session_duration = (times[-1] - times[0]).total_seconds()

    # Rhythm
    pauses = sum(1 for i in intervals if i > 3000)
    pause_ratio = pauses / len(intervals)
    idle_gaps = sum(1 for i in intervals if i > 10000)

    # Event distribution
    event_types = [e["eventType"] for e in events]
    api_call_ratio = event_types.count("api_call") / len(event_types)
    click_ratio = event_types.count("click") / len(event_types)
    scroll_ratio = event_types.count("scroll") / len(event_types)

    return {
        "mean_interval": mean_interval,
        "std_interval": std_interval,
        "cv_interval": cv_interval,
        "min_interval": min_interval,
        "max_interval": max_interval,
        "pct_under_200ms": pct_under_200ms,
        "pct_under_500ms": pct_under_500ms,
        "skew_ratio": skew_ratio,
        "avg_mouse_speed": avg_mouse_speed,
        "std_mouse_speed": std_mouse_speed,
        "cv_mouse_speed": cv_mouse_speed,
        "high_speed_ratio": high_speed_ratio,
        "max_mouse_speed": max_mouse_speed,
        "curve_ratio": curve_ratio,
        "avg_key_delay": avg_key_delay,
        "avg_error_rate": avg_error_rate,
        "max_error_rate": max_error_rate,
        "avg_burst_length": avg_burst_length,
        "api_ratio": api_ratio,
        "unique_ratio": unique_ratio,
        "revisit_ratio": revisit_ratio,
        "session_duration": session_duration,
        "pause_ratio": pause_ratio,
        "idle_gaps": idle_gaps,
        "click_ratio": click_ratio,
        "scroll_ratio": scroll_ratio,
        "num_events": len(events),
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 70)
    print("  ML BOT DETECTOR v2 — Behavioral Training (no /api/ shortcut)")
    print("=" * 70)

    # Load ALL data
    print("\n1. Loading data...")
    all_sessions = []

    for path in [
        "./bot_activity_sessions/all_sessions.json",
        "./challenge_bot_data/challenge_bot_sessions.json",
        "./ml/adversarial_data/adversarial_sessions.json",
    ]:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                all_sessions.extend(data)
                print(f"   Loaded {len(data)} from {path}")

    print(f"   Total: {len(all_sessions)} sessions")

    # Extract features
    print("\n2. Extracting features...")
    features = []
    labels = []

    for session in all_sessions:
        feat = extract_features(session)
        if feat is None:
            continue
        label = session.get("label", "unknown")
        if label in ("bot", "sneaky_bot", "challenge_bot"):
            labels.append(1)
        elif label == "human":
            labels.append(0)
        else:
            continue
        features.append(feat)

    print(f"   {len(features)} sessions with features")
    print(f"   Bots: {sum(labels)}, Humans: {len(labels) - sum(labels)}")

    feature_names = list(features[0].keys())
    X = np.array([[f[name] for name in feature_names] for f in features])
    y = np.array(labels)

    # Split
    print("\n3. Train/test split (80/20)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"   Train: {len(X_train)} | Test: {len(X_test)}")

    # Train
    print("\n4. Training GradientBoosting (300 trees, depth 6)...")
    model = GradientBoostingClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.08,
        min_samples_leaf=5,
        random_state=42,
    )
    model.fit(X_train, y_train)

    # Evaluate
    print("\n5. Results:")
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    report = classification_report(y_test, y_pred, target_names=["Human", "Bot"], output_dict=True)
    print(f"\n   Accuracy:  {report['accuracy']:.4f}")
    print(f"   Precision: {report['Bot']['precision']:.4f}")
    print(f"   Recall:    {report['Bot']['recall']:.4f}")
    print(f"   F1:        {report['Bot']['f1-score']:.4f}")

    cm = confusion_matrix(y_test, y_pred)
    print(f"\n   Confusion Matrix:")
    print(f"   {'':15} Pred Human  Pred Bot")
    print(f"   {'Actual Human':15} {cm[0][0]:>9}  {cm[0][1]:>8}")
    print(f"   {'Actual Bot':15} {cm[1][0]:>9}  {cm[1][1]:>8}")

    # Feature importance
    print(f"\n6. Top 15 Feature Importance:")
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1]
    for i in range(min(15, len(feature_names))):
        idx = indices[i]
        print(f"   {i+1:2}. {feature_names[idx]:25} {importances[idx]:.4f}")

    # Save model
    model_path = os.path.join(OUTPUT_DIR, "bot_detector_v2.pkl")
    with open(model_path, "wb") as f:
        pickle.dump({"model": model, "feature_names": feature_names, "version": "2.0"}, f)
    print(f"\n7. Model saved: {model_path}")

    # Save results
    results = {
        "version": "2.0",
        "training_data": "original + adversarial (no /api/ bots)",
        "total_samples": len(features),
        "accuracy": float(report["accuracy"]),
        "precision": float(report["Bot"]["precision"]),
        "recall": float(report["Bot"]["recall"]),
        "f1": float(report["Bot"]["f1-score"]),
        "confusion_matrix": {"tn": int(cm[0][0]), "fp": int(cm[0][1]), "fn": int(cm[1][0]), "tp": int(cm[1][1])},
        "top_features": {feature_names[indices[i]]: float(importances[indices[i]]) for i in range(len(feature_names))},
    }
    with open(os.path.join(OUTPUT_DIR, "training_results_v2.json"), "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'=' * 70}")


if __name__ == "__main__":
    main()
