"""
Save real human browsing data from the SDK dashboard to the training dataset.
This adds your actual browsing session to the ML training data.
"""
import requests
import json
import os
from datetime import datetime

# Get all sessions from dashboard
r = requests.get('http://localhost:5000/api/sdk/dashboard?apiKey=shopmax-demo-key')
d = r.json()

# Find human sessions (not bot, 5+ events)
human_sessions = [s for s in d['sessions'] if not s['isBot'] and s['eventCount'] >= 5]

print(f"Found {len(human_sessions)} human session(s)")

if not human_sessions:
    print("No human sessions found. Browse the site first!")
    exit()

# Get full session details for each
OUTPUT_DIR = "./ml/real_human_data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

all_sessions = []

for session_info in human_sessions:
    sid = session_info['sessionId']
    
    # Get detailed session from the API
    r2 = requests.get(f'http://localhost:5000/api/sdk/session/{sid}?apiKey=shopmax-demo-key')
    if r2.status_code == 200:
        detail = r2.json()
        
        # Format as training data
        training_session = {
            "sessionId": detail['sessionId'],
            "userId": "real-human-uriya",
            "userAgent": detail['userAgent'],
            "ipAddress": "192.168.1.1",
            "events": detail.get('events', []),
            "label": "human",
            "source": "real_browsing",
            "collected_at": datetime.now().isoformat(),
            "score": detail['lastScore'],
            "eventCount": detail['eventCount'],
        }
        all_sessions.append(training_session)
        print(f"  Saved session {sid[:30]}... ({detail['eventCount']} events, score={detail['lastScore']:.3f})")

# Save to file
output_path = os.path.join(OUTPUT_DIR, f"real_human_sessions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(all_sessions, f, ensure_ascii=False, indent=2)

print(f"\nSaved {len(all_sessions)} session(s) to {output_path}")
print(f"This data can be used to retrain the ML model with: python ml/train_v2.py")

# Also append to the main training dataset
main_dataset = "./bot_activity_sessions/all_sessions.json"
if os.path.exists(main_dataset):
    with open(main_dataset, "r", encoding="utf-8") as f:
        existing = json.load(f)
    
    # Add new human sessions
    for s in all_sessions:
        # Convert to the format the training pipeline expects
        training_entry = {
            "sessionId": s["sessionId"],
            "userId": s["userId"],
            "userAgent": s["userAgent"],
            "ipAddress": s["ipAddress"],
            "events": s["events"],
            "label": "human",
        }
        existing.append(training_entry)
    
    with open(main_dataset, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    
    print(f"Also appended to {main_dataset} (now {len(existing)} total sessions)")
