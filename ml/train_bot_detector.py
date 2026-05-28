"""
ML Bot Detector — Train a model from our session data.

Uses the labeled session data we already generated to train a
scikit-learn classifier that can detect bots from behavioral features.

Features extracted per session:
- Timing: mean interval, std interval, CV, min interval, max interval
- Mouse: avg speed, speed CV, high-speed ratio, curve ratio
- Keyboard: avg inter-key delay, error rate, burst length
- Navigation: API ratio, unique endpoint ratio, session duration
- Rhythm: pause ratio, idle gap count

Output:
- Trained model (pickle)
- Feature importance ranking
- Classification report
- Confusion matrix
"""

import json
import os
import pickle
from datetime import datetime

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

OUTPUT_DIR = "./ml/output"


def extract_features(session: dict) -> dict:
    """Extract numerical features from a session for ML training."""
    events = session.get("events", [])
    if len(events) < 2:
        return None

    # Parse timestamps
    times = []
    for e in events:
        ts = e["timestamp"].replace("Z", "+00:00")
        times.append(datetime.fromisoformat(ts))

    # === Timing features ===
    intervals = [(times[i] - times[i-1]).total_seconds() * 1000 for i in range(1, len(times))]
    mean_interval = np.mean(intervals)
    std_interval = np.std(intervals)
    cv_interval = std_interval / mean_interval if mean_interval > 0 else 0
    min_interval = np.min(intervals)
    max_interval = np.max(intervals)
    pct_under_200ms = sum(1 for i in intervals if i < 200) / len(intervals)
    pct_under_500ms = sum(1 for i in intervals if i < 500) / len(intervals)

    # === Mouse features ===
    mouse_speeds = [e["mouse"]["speed"] for e in events if e.get("mouse") and e["mouse"].get("speed")]
    if mouse_speeds:
        avg_mouse_speed = np.mean(mouse_speeds)
        std_mouse_speed = np.std(mouse_speeds)
        cv_mouse_speed = std_mouse_speed / avg_mouse_speed if avg_mouse_speed > 0 else 0
        high_speed_ratio = sum(1 for s in mouse_speeds if s > 1000) / len(mouse_speeds)
    else:
        avg_mouse_speed = 0
        std_mouse_speed = 0
        cv_mouse_speed = 0
        high_speed_ratio = 0

    # Curve ratio
    mouse_events = [e for e in events if e.get("mouse")]
    if mouse_events:
        has_curve_count = sum(1 for e in mouse_events if e["mouse"].get("hasCurve") == True)
        curve_ratio = has_curve_count / len(mouse_events)
    else:
        curve_ratio = 0.5  # neutral if no mouse data

    # === Keyboard features ===
    key_events = [e for e in events if e.get("keyboard")]
    if key_events:
        delays = [e["keyboard"]["interKeyDelayMs"] for e in key_events if e["keyboard"].get("interKeyDelayMs")]
        errors = [e["keyboard"]["errorRate"] for e in key_events if e["keyboard"].get("errorRate") is not None]
        bursts = [e["keyboard"]["burstLength"] for e in key_events if e["keyboard"].get("burstLength")]

        avg_key_delay = np.mean(delays) if delays else 0
        avg_error_rate = np.mean(errors) if errors else 0
        avg_burst_length = np.mean(bursts) if bursts else 0
    else:
        avg_key_delay = 0
        avg_error_rate = 0
        avg_burst_length = 0

    # === Navigation features ===
    endpoints = [e["endpoint"] for e in events if e.get("endpoint")]
    api_endpoints = [ep for ep in endpoints if ep.startswith("/api/")]
    api_ratio = len(api_endpoints) / len(endpoints) if endpoints else 0
    unique_ratio = len(set(endpoints)) / len(endpoints) if endpoints else 0

    # Session duration
    session_duration = (times[-1] - times[0]).total_seconds()

    # === Rhythm features ===
    pauses = sum(1 for i in intervals if i > 3000)
    pause_ratio = pauses / len(intervals)
    idle_gaps = sum(1 for i in intervals if i > 10000)

    # Event type distribution
    event_types = [e["eventType"] for e in events]
    api_call_ratio = event_types.count("api_call") / len(event_types)
    click_ratio = event_types.count("click") / len(event_types)
    scroll_ratio = event_types.count("scroll") / len(event_types)
    nav_ratio = event_types.count("navigation") / len(event_types)

    return {
        # Timing
        "mean_interval": mean_interval,
        "std_interval": std_interval,
        "cv_interval": cv_interval,
        "min_interval": min_interval,
        "max_interval": max_interval,
        "pct_under_200ms": pct_under_200ms,
        "pct_under_500ms": pct_under_500ms,
        # Mouse
        "avg_mouse_speed": avg_mouse_speed,
        "std_mouse_speed": std_mouse_speed,
        "cv_mouse_speed": cv_mouse_speed,
        "high_speed_ratio": high_speed_ratio,
        "curve_ratio": curve_ratio,
        # Keyboard
        "avg_key_delay": avg_key_delay,
        "avg_error_rate": avg_error_rate,
        "avg_burst_length": avg_burst_length,
        # Navigation
        "api_ratio": api_ratio,
        "unique_ratio": unique_ratio,
        "session_duration": session_duration,
        # Rhythm
        "pause_ratio": pause_ratio,
        "idle_gaps": idle_gaps,
        # Event distribution
        "api_call_ratio": api_call_ratio,
        "click_ratio": click_ratio,
        "scroll_ratio": scroll_ratio,
        "nav_ratio": nav_ratio,
        # Meta
        "num_events": len(events),
    }


def load_sessions():
    """Load all labeled session data."""
    sessions = []

    # Load from bot_activity_sessions (labeled data)
    data_file = "./bot_activity_sessions/all_sessions.json"
    if os.path.exists(data_file):
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            sessions.extend(data)
        print(f"  Loaded {len(data)} sessions from {data_file}")

    # Load challenge bot data
    challenge_file = "./challenge_bot_data/challenge_bot_sessions.json"
    if os.path.exists(challenge_file):
        with open(challenge_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            sessions.extend(data)
        print(f"  Loaded {len(data)} sessions from {challenge_file}")

    return sessions


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 70)
    print("  ML BOT DETECTOR — Training Pipeline")
    print("=" * 70)

    # Load data
    print("\n1. Loading session data...")
    sessions = load_sessions()
    print(f"   Total sessions: {len(sessions)}")

    # Extract features
    print("\n2. Extracting features...")
    features = []
    labels = []
    skipped = 0

    for session in sessions:
        feat = extract_features(session)
        if feat is None:
            skipped += 1
            continue

        label = session.get("label", "unknown")
        # Binary classification: bot (1) vs human (0)
        if label in ("bot", "sneaky_bot", "challenge_bot"):
            labels.append(1)
        elif label == "human":
            labels.append(0)
        else:
            skipped += 1
            continue

        features.append(feat)

    print(f"   Extracted features from {len(features)} sessions (skipped {skipped})")
    print(f"   Bots: {sum(labels)}, Humans: {len(labels) - sum(labels)}")

    # Convert to numpy arrays
    feature_names = list(features[0].keys())
    X = np.array([[f[name] for name in feature_names] for f in features])
    y = np.array(labels)

    # Split train/test
    print("\n3. Splitting data (80% train, 20% test)...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"   Train: {len(X_train)} samples")
    print(f"   Test:  {len(X_test)} samples")

    # Train Gradient Boosting model
    print("\n4. Training Gradient Boosting Classifier...")
    model = GradientBoostingClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
    )
    model.fit(X_train, y_train)

    # Evaluate
    print("\n5. Evaluating model...")
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    print("\n   Classification Report:")
    report = classification_report(y_test, y_pred, target_names=["Human", "Bot"])
    print(report)

    cm = confusion_matrix(y_test, y_pred)
    print(f"   Confusion Matrix:")
    print(f"   {'':15} Predicted Human  Predicted Bot")
    print(f"   {'Actual Human':15} {cm[0][0]:>14}  {cm[0][1]:>12}")
    print(f"   {'Actual Bot':15} {cm[1][0]:>14}  {cm[1][1]:>12}")

    # Feature importance
    print("\n6. Feature Importance (top 10):")
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1]
    for i in range(min(10, len(feature_names))):
        idx = indices[i]
        print(f"   {i+1:2}. {feature_names[idx]:25} {importances[idx]:.4f}")

    # Save model
    model_path = os.path.join(OUTPUT_DIR, "bot_detector_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump({"model": model, "feature_names": feature_names}, f)
    print(f"\n7. Model saved to {model_path}")

    # Save results
    results = {
        "model_type": "GradientBoostingClassifier",
        "n_estimators": 200,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "accuracy": float((y_pred == y_test).mean()),
        "classification_report": classification_report(y_test, y_pred, target_names=["Human", "Bot"], output_dict=True),
        "feature_importance": {feature_names[indices[i]]: float(importances[indices[i]]) for i in range(len(feature_names))},
        "confusion_matrix": {"tn": int(cm[0][0]), "fp": int(cm[0][1]), "fn": int(cm[1][0]), "tp": int(cm[1][1])},
    }

    results_path = os.path.join(OUTPUT_DIR, "training_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"   Results saved to {results_path}")

    # Test on a few examples
    print("\n8. Sample predictions on test set:")
    for i in range(min(5, len(X_test))):
        prob = y_prob[i]
        actual = "Bot" if y_test[i] == 1 else "Human"
        predicted = "Bot" if y_pred[i] == 1 else "Human"
        print(f"   Sample {i+1}: actual={actual:6} predicted={predicted:6} confidence={prob:.3f}")

    print(f"\n{'=' * 70}")
    print(f"  DONE. Model ready at {model_path}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
