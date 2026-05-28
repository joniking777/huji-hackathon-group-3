"""Visualize one of the decision trees from the ML model."""
import pickle
import numpy as np
from sklearn.tree import export_text

# Load model
with open('./ml/output/bot_detector_v2.pkl', 'rb') as f:
    data = pickle.load(f)

model = data['model']
features = data['feature_names']

print("=" * 70)
print("  ML MODEL ANATOMY")
print("=" * 70)

print(f"\n  Model type: {type(model).__name__}")
print(f"  Number of trees: {len(model.estimators_)}")
print(f"  Max depth per tree: {model.max_depth}")
print(f"  Total features: {len(features)}")

# Show top features
importances = model.feature_importances_
indices = np.argsort(importances)[::-1]
print(f"\n  TOP 10 FEATURES BY IMPORTANCE:")
for i in range(10):
    idx = indices[i]
    bar = "█" * int(importances[idx] * 50)
    print(f"    {i+1:2}. {features[idx]:25} {importances[idx]:.4f} {bar}")

# Visualize the FIRST tree (it's the most important — sets the baseline)
print(f"\n{'=' * 70}")
print(f"  FIRST DECISION TREE (out of 300)")
print(f"  This tree decides the initial bot/human prediction")
print(f"  Subsequent trees correct its mistakes")
print(f"{'=' * 70}\n")

first_tree = model.estimators_[0][0]
tree_text = export_text(first_tree, feature_names=features, max_depth=4)
print(tree_text)

# Show how a sample flows through the tree
print(f"{'=' * 70}")
print(f"  EXAMPLE: How a bot session gets classified")
print(f"{'=' * 70}\n")

# Bot-like sample
bot_sample = {f: 0 for f in features}
bot_sample.update({
    'mean_interval': 100,
    'cv_interval': 0.05,
    'pct_under_200ms': 0.9,
    'avg_mouse_speed': 5000,
    'cv_mouse_speed': 0.1,
    'avg_error_rate': 0.0,
    'max_error_rate': 0.0,
    'api_ratio': 0.8,
    'revisit_ratio': 0.0,
    'session_duration': 5,
    'pause_ratio': 0.0,
    'num_events': 20,
})

X = np.array([[bot_sample.get(f, 0) for f in features]])
prob = model.predict_proba(X)[0]
pred = model.predict(X)[0]

print(f"  Input (bot-like session):")
for f, v in bot_sample.items():
    if v != 0:
        print(f"    {f:25} = {v}")

print(f"\n  Prediction: {'BOT' if pred == 1 else 'HUMAN'}")
print(f"  Bot probability: {prob[1]*100:.1f}%")
print(f"  Confidence: {max(prob)*100:.1f}%")

# Now a human-like sample
print(f"\n{'=' * 70}")
human_sample = {f: 0 for f in features}
human_sample.update({
    'mean_interval': 3000,
    'cv_interval': 1.2,
    'pct_under_200ms': 0.0,
    'avg_mouse_speed': 700,
    'cv_mouse_speed': 0.4,
    'avg_error_rate': 0.08,
    'max_error_rate': 0.12,
    'api_ratio': 0.0,
    'revisit_ratio': 0.2,
    'session_duration': 60,
    'pause_ratio': 0.2,
    'num_events': 15,
})

X = np.array([[human_sample.get(f, 0) for f in features]])
prob = model.predict_proba(X)[0]
pred = model.predict(X)[0]

print(f"  Input (human-like session):")
for f, v in human_sample.items():
    if v != 0:
        print(f"    {f:25} = {v}")

print(f"\n  Prediction: {'BOT' if pred == 1 else 'HUMAN'}")
print(f"  Bot probability: {prob[1]*100:.1f}%")
print(f"  Confidence: {max(prob)*100:.1f}%")
