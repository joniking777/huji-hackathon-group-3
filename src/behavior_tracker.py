"""Tracks and records bot behavior data for analysis.

Outputs to ./bot_behavior/ with:
- Individual agent event logs (what each bot did, when, how long)
- Aggregated timeline (all events in chronological order)
- Concurrency snapshot (how many bots were active at each moment)
- Summary statistics
"""

import json
import os
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from threading import Lock


@dataclass
class BotEvent:
    """A single event in a bot's lifecycle."""
    agent_name: str
    event_type: str  # "started", "waiting_semaphore", "acquired_semaphore", "fetch_start", "fetch_end", "parse_start", "parse_end", "write_start", "write_end", "completed", "failed"
    timestamp: str
    elapsed_since_start_ms: float
    details: dict = field(default_factory=dict)


class BehaviorTracker:
    """Collects behavior data from all agents during execution."""

    def __init__(self, output_dir: str = "./bot_behavior"):
        self.output_dir = output_dir
        self.events: list[BotEvent] = []
        self._lock = Lock()
        self._global_start: float = 0.0
        self._active_agents: dict[str, float] = {}  # agent_name -> start_time
        self._concurrency_snapshots: list[dict] = []

    def start_tracking(self) -> None:
        """Mark the global start time."""
        self._global_start = time.time()
        os.makedirs(self.output_dir, exist_ok=True)

    def record_event(self, agent_name: str, event_type: str, details: dict | None = None) -> None:
        """Record a bot behavior event."""
        now = time.time()
        elapsed = (now - self._global_start) * 1000  # ms

        event = BotEvent(
            agent_name=agent_name,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            elapsed_since_start_ms=round(elapsed, 2),
            details=details or {},
        )

        with self._lock:
            self.events.append(event)

            # Track concurrency
            if event_type == "fetch_start":
                self._active_agents[agent_name] = now
            elif event_type in ("fetch_end", "failed"):
                self._active_agents.pop(agent_name, None)

            self._concurrency_snapshots.append({
                "elapsed_ms": round(elapsed, 2),
                "active_count": len(self._active_agents),
                "event": f"{agent_name}:{event_type}",
            })

    def save_all(self) -> None:
        """Write all behavior data to the output directory."""
        os.makedirs(self.output_dir, exist_ok=True)

        # 1. Full event timeline
        timeline_path = os.path.join(self.output_dir, "timeline.json")
        with open(timeline_path, "w", encoding="utf-8") as f:
            json.dump(
                [asdict(e) for e in sorted(self.events, key=lambda e: e.elapsed_since_start_ms)],
                f, ensure_ascii=False, indent=2,
            )

        # 2. Per-agent behavior logs
        agents_dir = os.path.join(self.output_dir, "agents")
        os.makedirs(agents_dir, exist_ok=True)

        agent_events: dict[str, list[BotEvent]] = {}
        for event in self.events:
            agent_events.setdefault(event.agent_name, []).append(event)

        for agent_name, events in agent_events.items():
            agent_path = os.path.join(agents_dir, f"{agent_name}_behavior.json")
            with open(agent_path, "w", encoding="utf-8") as f:
                json.dump(
                    [asdict(e) for e in sorted(events, key=lambda e: e.elapsed_since_start_ms)],
                    f, ensure_ascii=False, indent=2,
                )

        # 3. Concurrency over time
        concurrency_path = os.path.join(self.output_dir, "concurrency.json")
        with open(concurrency_path, "w", encoding="utf-8") as f:
            json.dump(self._concurrency_snapshots, f, ensure_ascii=False, indent=2)

        # 4. Summary statistics
        summary = self._compute_summary()
        summary_path = os.path.join(self.output_dir, "summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

    def _compute_summary(self) -> dict:
        """Compute aggregate statistics about bot behavior."""
        if not self.events:
            return {"total_events": 0}

        total_duration_ms = max(e.elapsed_since_start_ms for e in self.events)

        # Per-agent durations
        agent_starts: dict[str, float] = {}
        agent_ends: dict[str, float] = {}
        agent_items: dict[str, int] = {}
        agent_statuses: dict[str, str] = {}

        for event in self.events:
            name = event.agent_name
            if event.event_type == "started":
                agent_starts[name] = event.elapsed_since_start_ms
            elif event.event_type == "completed":
                agent_ends[name] = event.elapsed_since_start_ms
                agent_statuses[name] = "success"
                agent_items[name] = event.details.get("item_count", 0)
            elif event.event_type == "failed":
                agent_ends[name] = event.elapsed_since_start_ms
                agent_statuses[name] = "failed"

        agent_durations = {}
        for name in agent_starts:
            if name in agent_ends:
                agent_durations[name] = round(agent_ends[name] - agent_starts[name], 2)

        durations_list = list(agent_durations.values())

        # Peak concurrency
        peak_concurrency = max((s["active_count"] for s in self._concurrency_snapshots), default=0)

        # Wait times (time between started and fetch_start = semaphore wait)
        wait_times: list[float] = []
        fetch_starts: dict[str, float] = {}
        for event in self.events:
            if event.event_type == "fetch_start":
                fetch_starts[event.agent_name] = event.elapsed_since_start_ms

        for name, start in agent_starts.items():
            if name in fetch_starts:
                wait_times.append(round(fetch_starts[name] - start, 2))

        succeeded = sum(1 for s in agent_statuses.values() if s == "success")
        failed = sum(1 for s in agent_statuses.values() if s == "failed")

        return {
            "total_agents": len(agent_starts),
            "succeeded": succeeded,
            "failed": failed,
            "total_events": len(self.events),
            "total_duration_ms": round(total_duration_ms, 2),
            "peak_concurrency": peak_concurrency,
            "agent_duration_stats_ms": {
                "min": round(min(durations_list), 2) if durations_list else 0,
                "max": round(max(durations_list), 2) if durations_list else 0,
                "avg": round(sum(durations_list) / len(durations_list), 2) if durations_list else 0,
            },
            "semaphore_wait_stats_ms": {
                "min": round(min(wait_times), 2) if wait_times else 0,
                "max": round(max(wait_times), 2) if wait_times else 0,
                "avg": round(sum(wait_times) / len(wait_times), 2) if wait_times else 0,
            },
            "total_items_extracted": sum(agent_items.values()),
            "by_type": self._stats_by_type(agent_durations, agent_items, agent_statuses),
        }

    def _stats_by_type(self, durations: dict, items: dict, statuses: dict) -> dict:
        """Break down stats by agent type."""
        types: dict[str, dict] = {}
        for name in durations:
            # Extract type from "headline_agent_042" -> "headline_agent"
            parts = name.rsplit("_", 1)
            agent_type = parts[0] if len(parts) > 1 and parts[1].isdigit() else name
            if agent_type not in types:
                types[agent_type] = {"count": 0, "succeeded": 0, "total_items": 0, "durations": []}
            types[agent_type]["count"] += 1
            if statuses.get(name) == "success":
                types[agent_type]["succeeded"] += 1
            types[agent_type]["total_items"] += items.get(name, 0)
            types[agent_type]["durations"].append(durations[name])

        # Compute averages
        result = {}
        for agent_type, stats in types.items():
            d = stats["durations"]
            result[agent_type] = {
                "count": stats["count"],
                "succeeded": stats["succeeded"],
                "total_items": stats["total_items"],
                "avg_duration_ms": round(sum(d) / len(d), 2) if d else 0,
            }
        return result
