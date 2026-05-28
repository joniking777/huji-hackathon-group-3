"""
Multi-Agent Web Scraper — 1,000 Agent Army
===========================================
Launches 1,000 concurrent agents (250 of each type) to scrape
the Ynet homepage. Agents are throttled via semaphore to avoid
overwhelming the target server.

Usage:
    python main.py
"""

import asyncio
import time

from src.agents import HeadlineAgent, ImageAgent, LinksAgent, MetadataAgent
from src.logger import setup_logging
from src.scraper_system import ScraperSystem

TARGET_URL = "https://www.ynet.co.il/home/0,7340,L-8,00.html"
OUTPUT_DIR = "./output"

# How many agents of each type to spawn
AGENTS_PER_TYPE = 250

# Max concurrent HTTP requests (prevents flooding the server)
MAX_CONCURRENT = 50


async def main():
    """Initialize and run the 1,000-agent scraper army."""
    setup_logging()

    system = ScraperSystem(output_dir=OUTPUT_DIR, max_concurrent=MAX_CONCURRENT)

    # Spawn 250 headline agents
    for i in range(AGENTS_PER_TYPE):
        system.register_agent(HeadlineAgent(
            target_url=TARGET_URL,
            output_dir=OUTPUT_DIR,
            name=f"headline_agent_{i:03d}",
        ))

    # Spawn 250 image agents
    for i in range(AGENTS_PER_TYPE):
        system.register_agent(ImageAgent(
            target_url=TARGET_URL,
            output_dir=OUTPUT_DIR,
            name=f"image_agent_{i:03d}",
        ))

    # Spawn 250 links agents
    for i in range(AGENTS_PER_TYPE):
        system.register_agent(LinksAgent(
            target_url=TARGET_URL,
            output_dir=OUTPUT_DIR,
            name=f"links_agent_{i:03d}",
        ))

    # Spawn 250 metadata agents
    for i in range(AGENTS_PER_TYPE):
        system.register_agent(MetadataAgent(
            target_url=TARGET_URL,
            output_dir=OUTPUT_DIR,
            name=f"metadata_agent_{i:03d}",
        ))

    print(f"\n  Army assembled: {len(system.agents)} agents ready")
    print(f"  Concurrency limit: {MAX_CONCURRENT} simultaneous requests")
    print(f"  Target: {TARGET_URL}\n")

    wall_start = time.time()

    # Launch the army
    results = await system.run_all()

    wall_end = time.time()
    print(f"\n  Wall clock time: {wall_end - wall_start:.2f}s")

    # Print aggregated summary
    system.print_summary(results)


if __name__ == "__main__":
    asyncio.run(main())
