"""Agent-aware logging wrapper."""

import logging
from datetime import datetime


class AgentLogger:
    """Logger that prefixes all messages with the agent's unique name."""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"agent.{agent_name}")
        self._start_time: datetime | None = None
        self._end_time: datetime | None = None

    def _format(self, message: str) -> str:
        return f"[{self.agent_name}] {message}"

    def info(self, message: str) -> None:
        self.logger.info(self._format(message))

    def warning(self, message: str) -> None:
        self.logger.warning(self._format(message))

    def error(self, message: str) -> None:
        self.logger.error(self._format(message))

    def debug(self, message: str) -> None:
        self.logger.debug(self._format(message))

    def mark_start(self) -> datetime:
        """Record and return the start time."""
        self._start_time = datetime.now()
        self.info(f"Started at {self._start_time.isoformat()}")
        return self._start_time

    def mark_end(self) -> datetime:
        """Record and return the end time."""
        self._end_time = datetime.now()
        self.info(f"Finished at {self._end_time.isoformat()}")
        if self._start_time:
            duration = (self._end_time - self._start_time).total_seconds()
            self.info(f"Duration: {duration:.2f}s")
        return self._end_time


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logging format."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
