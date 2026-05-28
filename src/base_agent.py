"""Abstract base class for all scraping agents."""

import asyncio
import json
import os
from abc import ABC, abstractmethod
from dataclasses import asdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import aiohttp

from src.logger import AgentLogger
from src.models import AgentResult, ExtractedItem, OutputMetadata

if TYPE_CHECKING:
    from src.behavior_tracker import BehaviorTracker


class BaseAgent(ABC):
    """Abstract base class for all scraping agents."""

    def __init__(self, name: str, target_url: str, output_dir: str):
        self.name = name
        self.target_url = target_url
        self.output_dir = output_dir
        self.logger = AgentLogger(name)
        # These are injected by ScraperSystem before run()
        self._shared_session: aiohttp.ClientSession | None = None
        self._semaphore: asyncio.Semaphore | None = None
        self._tracker: "BehaviorTracker | None" = None

    @abstractmethod
    async def parse(self, html: str) -> list[ExtractedItem]:
        """Parse HTML and return extracted items."""
        ...

    async def fetch_page(self) -> str:
        """Fetch the target page HTML content using shared session."""
        self.logger.info(f"Fetching {self.target_url}")
        if self._tracker:
            self._tracker.record_event(self.name, "fetch_start")

        session = self._shared_session
        if session is None:
            session = aiohttp.ClientSession()

        try:
            async with session.get(
                self.target_url,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                response.raise_for_status()
                html = await response.text()
                self.logger.info(f"Fetched {len(html)} bytes")
                if self._tracker:
                    self._tracker.record_event(self.name, "fetch_end", {"bytes": len(html)})
                return html
        finally:
            if self._shared_session is None:
                await session.close()

    async def write_output(self, items: list[ExtractedItem], error: dict | None = None) -> None:
        """Write extracted items to JSON output file."""
        os.makedirs(self.output_dir, exist_ok=True)

        output_path = os.path.join(self.output_dir, f"{self.name}_output.json")

        metadata = OutputMetadata(
            agent_name=self.name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            target_url=self.target_url,
            item_count=len(items),
        )

        output = {
            "metadata": asdict(metadata),
            "items": [asdict(item) for item in items],
        }

        if error:
            output["error"] = error

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Wrote {len(items)} items to {output_path}")

    async def run(self) -> AgentResult:
        """Execute the full agent pipeline: fetch → parse → write."""
        if self._tracker:
            self._tracker.record_event(self.name, "started")
        # Respect concurrency limit if semaphore is set
        if self._semaphore:
            if self._tracker:
                self._tracker.record_event(self.name, "waiting_semaphore")
            async with self._semaphore:
                if self._tracker:
                    self._tracker.record_event(self.name, "acquired_semaphore")
                return await self._execute()
        return await self._execute()

    async def _execute(self) -> AgentResult:
        """Internal execution logic."""
        start_time = self.logger.mark_start()

        try:
            html = await self.fetch_page()

            if self._tracker:
                self._tracker.record_event(self.name, "parse_start")
            items = await self.parse(html)
            if self._tracker:
                self._tracker.record_event(self.name, "parse_end", {"item_count": len(items)})

            if self._tracker:
                self._tracker.record_event(self.name, "write_start")
            await self.write_output(items)
            if self._tracker:
                self._tracker.record_event(self.name, "write_end")

            end_time = self.logger.mark_end()

            if self._tracker:
                self._tracker.record_event(self.name, "completed", {"item_count": len(items)})

            return AgentResult(
                agent_name=self.name,
                success=True,
                item_count=len(items),
                start_time=start_time,
                end_time=end_time,
            )

        except aiohttp.ClientResponseError as e:
            self.logger.error(f"HTTP error: {e.status} {e.message}")
            error_info = {
                "type": "HTTPError",
                "message": f"Failed to fetch page: {e.status} {e.message}",
                "status_code": e.status,
            }
            await self.write_output([], error=error_info)
            end_time = self.logger.mark_end()
            if self._tracker:
                self._tracker.record_event(self.name, "failed", {"error": str(e)})
            return AgentResult(
                agent_name=self.name,
                success=False,
                item_count=0,
                start_time=start_time,
                end_time=end_time,
                error=str(e),
            )

        except Exception as e:
            self.logger.error(f"Unexpected error: {type(e).__name__}: {e}")
            error_info = {
                "type": type(e).__name__,
                "message": str(e),
            }
            await self.write_output([], error=error_info)
            end_time = self.logger.mark_end()
            if self._tracker:
                self._tracker.record_event(self.name, "failed", {"error": str(e)})
            return AgentResult(
                agent_name=self.name,
                success=False,
                item_count=0,
                start_time=start_time,
                end_time=end_time,
                error=str(e),
            )
