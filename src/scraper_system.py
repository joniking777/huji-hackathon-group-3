"""Top-level orchestrator for all scraping agents."""

import asyncio
from datetime import datetime

import aiohttp

from src.base_agent import BaseAgent
from src.behavior_tracker import BehaviorTracker
from src.logger import AgentLogger
from src.models import AgentResult


class ScraperSystem:
    """Orchestrates concurrent execution of all registered scraping agents.

    Supports scaling to thousands of agents via:
    - Shared aiohttp session (connection pooling)
    - Semaphore-based concurrency limiting
    - Behavior tracking for observability
    """

    def __init__(self, output_dir: str = "./output", max_concurrent: int = 50):
        self.output_dir = output_dir
        self.max_concurrent = max_concurrent
        self.agents: list[BaseAgent] = []
        self.logger = AgentLogger("scraper_system")
        self.tracker = BehaviorTracker(output_dir="./bot_behavior")

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent. Raises ValueError if name is duplicate."""
        existing_names = {a.name for a in self.agents}
        if agent.name in existing_names:
            raise ValueError(f"Agent with name '{agent.name}' is already registered")
        self.agents.append(agent)

    async def run_all(self) -> list[AgentResult]:
        """Launch all agents concurrently with controlled concurrency."""
        self.logger.info(f"Launching {len(self.agents)} agents (max {self.max_concurrent} concurrent)...")

        # Start behavior tracking
        self.tracker.start_tracking()

        # Shared resources for all agents
        semaphore = asyncio.Semaphore(self.max_concurrent)
        connector = aiohttp.TCPConnector(limit=self.max_concurrent, limit_per_host=self.max_concurrent)

        async with aiohttp.ClientSession(connector=connector) as session:
            # Inject shared session, semaphore, and tracker into each agent
            for agent in self.agents:
                agent._shared_session = session
                agent._semaphore = semaphore
                agent._tracker = self.tracker

            # Run all agents concurrently, catching exceptions per-agent
            results_or_exceptions = await asyncio.gather(
                *[agent.run() for agent in self.agents],
                return_exceptions=True,
            )

        results: list[AgentResult] = []
        for i, result in enumerate(results_or_exceptions):
            if isinstance(result, Exception):
                agent_name = self.agents[i].name
                self.logger.error(f"Agent '{agent_name}' raised unhandled exception: {result}")
                results.append(AgentResult(
                    agent_name=agent_name,
                    success=False,
                    item_count=0,
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    error=str(result),
                ))
            else:
                results.append(result)

        # Save all behavior data
        self.tracker.save_all()
        self.logger.info("Bot behavior data saved to ./bot_behavior/")

        return results

    def print_summary(self, results: list[AgentResult]) -> None:
        """Print execution summary — aggregated for large agent counts."""
        print("\n" + "=" * 60)
        print("  MULTI-AGENT SCRAPER - EXECUTION SUMMARY")
        print("=" * 60)

        succeeded = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        total_items = sum(r.item_count for r in results)

        # Timing stats
        durations = []
        for r in results:
            if r.start_time and r.end_time:
                durations.append((r.end_time - r.start_time).total_seconds())

        print(f"\n  Total agents: {len(results)}")
        print(f"  Succeeded:    {len(succeeded)}")
        print(f"  Failed:       {len(failed)}")
        print(f"  Total items:  {total_items}")

        if durations:
            avg_duration = sum(durations) / len(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            print(f"\n  Timing:")
            print(f"    Fastest agent: {min_duration:.2f}s")
            print(f"    Slowest agent: {max_duration:.2f}s")
            print(f"    Average:       {avg_duration:.2f}s")

        # Breakdown by agent type
        type_stats: dict[str, dict] = {}
        for r in results:
            # Extract type from name like "headline_agent_042"
            parts = r.agent_name.rsplit("_", 1)
            agent_type = parts[0] if len(parts) > 1 and parts[1].isdigit() else r.agent_name
            if agent_type not in type_stats:
                type_stats[agent_type] = {"count": 0, "succeeded": 0, "items": 0}
            type_stats[agent_type]["count"] += 1
            if r.success:
                type_stats[agent_type]["succeeded"] += 1
            type_stats[agent_type]["items"] += r.item_count

        print(f"\n  By agent type:")
        for agent_type, stats in sorted(type_stats.items()):
            print(f"    {agent_type}: {stats['succeeded']}/{stats['count']} ok, {stats['items']} items")

        # Show first few failures if any
        if failed:
            print(f"\n  First 10 failures:")
            for r in failed[:10]:
                print(f"    [{r.agent_name}] {r.error}")

        print("\n" + "=" * 60)
