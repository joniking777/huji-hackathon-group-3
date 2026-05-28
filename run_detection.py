"""
Send bot activity sessions to the AISecutity detection engine and display results.
"""

import json
import requests

API_URL = "http://localhost:5000/api/detection/analyze-batch"
SESSIONS_FILE = "./bot_activity_sessions/all_sessions.json"


def main():
    print("Loading sessions...")
    with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
        sessions = json.load(f)

    print(f"Loaded {len(sessions)} sessions. Sending to detection engine...\n")

    # Send in batches of 50 to avoid huge payloads
    batch_size = 50
    all_results = []

    for i in range(0, len(sessions), batch_size):
        batch = sessions[i:i + batch_size]
        # Remove the "label" field before sending (detector shouldn't see ground truth)
        clean_batch = []
        for s in batch:
            clean = {k: v for k, v in s.items() if k != "label"}
            clean_batch.append(clean)

        resp = requests.post(API_URL, json=clean_batch, timeout=30)
        if resp.status_code == 200:
            results = resp.json()
            # Re-attach labels for evaluation
            for j, result in enumerate(results):
                result["groundTruth"] = batch[j].get("label", "unknown")
            all_results.extend(results)
            print(f"  Batch {i // batch_size + 1}/{(len(sessions) + batch_size - 1) // batch_size}: {len(results)} analyzed")
        else:
            print(f"  Batch {i // batch_size + 1} FAILED: {resp.status_code} {resp.text[:200]}")

    print(f"\n{'=' * 70}")
    print(f"  DETECTION RESULTS — {len(all_results)} sessions analyzed")
    print(f"{'=' * 70}")

    # Categorize results
    true_positive = 0   # Bot correctly detected as bot
    false_negative = 0  # Bot missed (classified as human)
    true_negative = 0   # Human correctly classified as human
    false_positive = 0  # Human incorrectly flagged as bot
    sneaky_caught = 0
    sneaky_missed = 0

    bot_scores = []
    human_scores = []
    sneaky_scores = []

    for r in all_results:
        label = r["groundTruth"]
        is_ai = r["isLikelyAiAgent"]
        score = r["aiProbabilityScore"]

        if label == "bot":
            bot_scores.append(score)
            if is_ai:
                true_positive += 1
            else:
                false_negative += 1
        elif label == "human":
            human_scores.append(score)
            if is_ai:
                false_positive += 1
            else:
                true_negative += 1
        elif label == "sneaky_bot":
            sneaky_scores.append(score)
            if is_ai:
                sneaky_caught += 1
            else:
                sneaky_missed += 1

    total_bots = true_positive + false_negative
    total_humans = true_negative + false_positive
    total_sneaky = sneaky_caught + sneaky_missed

    print(f"\n  OBVIOUS BOTS ({total_bots} sessions):")
    print(f"    Detected:  {true_positive} ({true_positive/total_bots*100:.1f}%)")
    print(f"    Missed:    {false_negative} ({false_negative/total_bots*100:.1f}%)")
    print(f"    Avg score: {sum(bot_scores)/len(bot_scores):.3f}")

    print(f"\n  HUMANS ({total_humans} sessions):")
    print(f"    Correct:       {true_negative} ({true_negative/total_humans*100:.1f}%)")
    print(f"    False alarms:  {false_positive} ({false_positive/total_humans*100:.1f}%)")
    print(f"    Avg score: {sum(human_scores)/len(human_scores):.3f}")

    print(f"\n  SNEAKY BOTS ({total_sneaky} sessions):")
    print(f"    Caught:  {sneaky_caught} ({sneaky_caught/total_sneaky*100:.1f}%)")
    print(f"    Evaded:  {sneaky_missed} ({sneaky_missed/total_sneaky*100:.1f}%)")
    print(f"    Avg score: {sum(sneaky_scores)/len(sneaky_scores):.3f}")

    # Overall metrics
    precision = true_positive / max(1, true_positive + false_positive)
    recall = true_positive / max(1, true_positive + false_negative)
    f1 = 2 * precision * recall / max(0.001, precision + recall)

    print(f"\n  OVERALL METRICS:")
    print(f"    Precision: {precision:.3f} (of those flagged as bot, how many actually are)")
    print(f"    Recall:    {recall:.3f} (of actual bots, how many were caught)")
    print(f"    F1 Score:  {f1:.3f}")

    print(f"\n{'=' * 70}")

    # Show some example detections
    print(f"\n  TOP 5 HIGHEST SCORING SESSIONS (most bot-like):")
    sorted_results = sorted(all_results, key=lambda r: r["aiProbabilityScore"], reverse=True)
    for r in sorted_results[:5]:
        print(f"    [{r['groundTruth']:10}] {r['sessionId']:25} score={r['aiProbabilityScore']:.4f}  signals: ", end="")
        for s in r.get("signals", []):
            print(f"{s['signalName']}={s['score']:.2f} ", end="")
        print()

    print(f"\n  TOP 5 LOWEST SCORING SESSIONS (most human-like):")
    for r in sorted_results[-5:]:
        print(f"    [{r['groundTruth']:10}] {r['sessionId']:25} score={r['aiProbabilityScore']:.4f}  signals: ", end="")
        for s in r.get("signals", []):
            print(f"{s['signalName']}={s['score']:.2f} ", end="")
        print()

    # Save full results
    output_path = "./bot_activity_sessions/detection_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n  Full results saved to: {output_path}")


if __name__ == "__main__":
    main()
