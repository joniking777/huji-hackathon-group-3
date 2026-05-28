"""Save the latest session as 'human pretending to be robot' data."""
import requests, json, os
from datetime import datetime

r = requests.get('http://localhost:5000/api/sdk/dashboard?apiKey=shopmax-demo-key')
d = r.json()

# Get the most recent session (should be the one just recorded)
sessions = sorted(d['sessions'], key=lambda x: x['lastSeenAt'], reverse=True)

if not sessions:
    print("No sessions found!")
    exit()

latest = sessions[0]
sid = latest['sessionId']

# Get full details
r2 = requests.get(f'http://localhost:5000/api/sdk/session/{sid}?apiKey=shopmax-demo-key')
detail = r2.json()

OUTPUT_DIR = "./ml/human_pretending_robot"
os.makedirs(OUTPUT_DIR, exist_ok=True)

session_data = {
    "sessionId": detail['sessionId'],
    "userId": "uriya-pretending-robot",
    "userAgent": detail['userAgent'],
    "ipAddress": "192.168.1.1",
    "events": detail.get('events', []),
    "label": "human_pretending_robot",
    "source": "real_browsing_acting_as_bot",
    "collected_at": datetime.now().isoformat(),
    "score": detail['lastScore'],
    "eventCount": detail['eventCount'],
    "isBot": detail['isBot'],
}

output_path = os.path.join(OUTPUT_DIR, f"human_as_robot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump([session_data], f, ensure_ascii=False, indent=2)

print(f"Session saved to: {output_path}")
print(f"  Events: {detail['eventCount']}")
print(f"  Score: {detail['lastScore']:.4f} ({(detail['lastScore']*100):.1f}%)")
print(f"  Detected as bot: {detail['isBot']}")
print(f"  Label: human_pretending_robot")

if detail.get('signals'):
    print(f"\n  Top signals:")
    for s in sorted(detail['signals'], key=lambda x: x['score'], reverse=True)[:5]:
        print(f"    {s['signalName']:25} {s['score']:.2f}")
