"""Data models for the multi-agent web scraper."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AgentResult:
    """Result of an agent's execution."""
    agent_name: str
    success: bool
    item_count: int
    start_time: datetime
    end_time: datetime
    error: str | None = None


@dataclass
class OutputMetadata:
    """Metadata section included in every output JSON file."""
    agent_name: str
    timestamp: str
    target_url: str
    item_count: int


@dataclass
class ExtractedItem:
    """Base class for extracted content items."""
    pass


@dataclass
class HeadlineItem(ExtractedItem):
    """A single extracted headline."""
    text: str
    section: str
    position: int


@dataclass
class ImageItem(ExtractedItem):
    """A single extracted image."""
    url: str | None
    alt_text: str
    title: str


@dataclass
class LinkItem(ExtractedItem):
    """A single extracted link."""
    url: str
    anchor_text: str
    parent_section: str


@dataclass
class MetadataItem(ExtractedItem):
    """A single metadata entry."""
    type: str
    value: str
