"""Analyze challenge bot data to find new detection signals."""
import json
from datetime import datetime

data = json.load(open('challenge_bot_data/challenge_bot_sessions.json'))
humans = json.load(open('bot_activity_sessions/human_sessions.json'))

def analyze_sessions(sessions, label):
    all_cvs = []
    all_speeds = []
    all_speed_cvs = []
    all_nav_eff = []
    all_endpoint_diversity = []
    all_mouse_speed_consistency = []
    all_session_lengths = []
    all_api_ratios = []

    for s in sessions:
        events = s['events']
        times = [datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')) for e in events]
        intervals = [(times[i] - times[i-1]).total_seconds() * 1000 for i in range(1, len(times))]

        if not intervals:
            continue

        # Timing CV
        mean = sum(intervals) / len(intervals)
        std = (sum((x - mean)**2 for x in intervals) / len(intervals)) ** 0.5
        cv = std / mean if mean > 0 else 0
        all_cvs.append(cv)

        # Mouse speed stats
        speeds = [e['mouse']['speed'] for e in events if e.get('mouse')]
        if speeds:
            smean = sum(speeds) / len(speeds)
            sstd = (sum((x - smean)**2 for x in speeds) / len(speeds)) ** 0.5
            scv = sstd / smean if smean > 0 else 0
            all_speeds.append(smean)
            all_speed_cvs.append(scv)

        # Navigation efficiency (unique endpoints / total)
        endpoints = [e['endpoint'] for e in events]
        nav_eff = len(set(endpoints)) / len(endpoints)
        all_nav_eff.append(nav_eff)

        # API call ratio
        api_calls = sum(1 for e in events if e['eventType'] == 'api_call' or e['endpoint'].startswith('/api/'))
        api_ratio = api_calls / len(events)
        all_api_ratios.append(api_ratio)

        # Session length (total time)
        if len(times) >= 2:
            duration = (times[-1] - times[0]).total_seconds()
            all_session_lengths.append(duration)

    print(f"\n  {label} ({len(sessions)} sessions):")
    print(f"    Timing CV:        min={min(all_cvs):.3f}  max={max(all_cvs):.3f}  avg={sum(all_cvs)/len(all_cvs):.3f}")
    if all_speeds:
        print(f"    Mouse speed avg:  min={min(all_speeds):.0f}  max={max(all_speeds):.0f}  avg={sum(all_speeds)/len(all_speeds):.0f}")
        print(f"    Mouse speed CV:   min={min(all_speed_cvs):.3f}  max={max(all_speed_cvs):.3f}  avg={sum(all_speed_cvs)/len(all_speed_cvs):.3f}")
    print(f"    Nav efficiency:   min={min(all_nav_eff):.3f}  max={max(all_nav_eff):.3f}  avg={sum(all_nav_eff)/len(all_nav_eff):.3f}")
    print(f"    API call ratio:   min={min(all_api_ratios):.3f}  max={max(all_api_ratios):.3f}  avg={sum(all_api_ratios)/len(all_api_ratios):.3f}")
    if all_session_lengths:
        print(f"    Session duration: min={min(all_session_lengths):.1f}s  max={max(all_session_lengths):.1f}s  avg={sum(all_session_lengths)/len(all_session_lengths):.1f}s")

    return {
        "timing_cv_avg": sum(all_cvs)/len(all_cvs),
        "speed_avg": sum(all_speeds)/len(all_speeds) if all_speeds else 0,
        "speed_cv_avg": sum(all_speed_cvs)/len(all_speed_cvs) if all_speed_cvs else 0,
        "nav_eff_avg": sum(all_nav_eff)/len(all_nav_eff),
        "api_ratio_avg": sum(all_api_ratios)/len(all_api_ratios),
        "session_duration_avg": sum(all_session_lengths)/len(all_session_lengths) if all_session_lengths else 0,
    }

print("=" * 70)
print("  COMPARING CHALLENGE BOTS vs HUMANS — Finding new detection signals")
print("=" * 70)

bot_stats = analyze_sessions(data, "CHALLENGE BOTS")
human_stats = analyze_sessions(humans, "HUMANS")

print("\n" + "=" * 70)
print("  KEY DIFFERENCES (signals to exploit):")
print("=" * 70)
print(f"\n  Mouse speed CV:  Bots={bot_stats['speed_cv_avg']:.3f}  Humans={human_stats['speed_cv_avg']:.3f}")
print(f"    → Bots have LOW mouse speed variance (speed is too consistent)")
print(f"\n  API call ratio:  Bots={bot_stats['api_ratio_avg']:.3f}  Humans={human_stats['api_ratio_avg']:.3f}")
print(f"    → Bots hit API endpoints more often")
print(f"\n  Nav efficiency:  Bots={bot_stats['nav_eff_avg']:.3f}  Humans={human_stats['nav_eff_avg']:.3f}")
print(f"    → Bots visit more unique pages per action (less revisiting)")
print(f"\n  Session duration: Bots={bot_stats['session_duration_avg']:.1f}s  Humans={human_stats['session_duration_avg']:.1f}s")
print(f"    → Bots have shorter sessions")
