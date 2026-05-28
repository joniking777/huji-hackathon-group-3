# Design Document

## Overview

A Python asyncio-based concurrent multi-agent web scraping system. The system orchestrates four specialized agents (Headline, Image, Links, Metadata) that independently scrape the Ynet homepage and produce individual JSON output files. The architecture emphasizes agent isolation, graceful error handling, and observability through structured logging.

## Architecture

The system follows a **coordinator-worker** pattern:

- A central `ScraperSystem` coordinator manages agent lifecycle (registration, concurrent launch, status collection)
- Each agent is an independent async task that fetches, parses, and writes output without knowledge of other agents
- Agents share no mutable state; communication flows only through the coordinator's status reporting

```
┌─────────────────────────────────────────────────┐
│                 ScraperSystem                     │
│  ┌───────────┐  ┌──────────┐  ┌─────────────┐  │
│  │  Agent    │  │  Config  │  │  Summary    │  │
│  │  Registry │  │  Manager │  │  Reporter   │  │
│  └───────────┘  └──────────┘  └─────────────┘  │
│         │                                        │
│    asyncio.gather(...)                           │
│    ┌────┼────────┬──────────┬──────────┐        │
│    ▼    ▼        ▼          ▼          ▼        │
│  ┌────┐ ┌────┐ ┌────┐ ┌────────┐              │
│  │Head│ │Img │ │Link│ │Metadata│              │
│  │line│ │Age │ │Age │ │ Agent  │              │
│  │Agt │ │nt  │ │nt  │ │        │              │
│  └──┬─┘ └──┬─┘ └──┬─┘ └───┬────┘              │
│     │       │      │       │                    │
└─────┼───────┼──────┼───────┼────────────────────┘
      ▼       ▼      ▼       ▼
  ┌──────┐┌──────┐┌──────┐┌──────┐
  │.json ││.json ││.json ││.json │
  └──────┘└──────┘└──────┘└──────┘
```

## Components and Interfaces

### ScraperSystem

The top-level orchestrator responsible for:
- Registering agents with unique names
- Launching all agents concurrently via `asyncio.gather(return_exceptions=True)`
- Collecting execution results and producing a summary report
- Managing the output directory configuration

### BaseAgent (Abstract)

An abstract base class defining the agent contract:
- `fetch_page()` — fetches the target URL using `aiohttp`
- `parse(html: str)` — extracts content (implemented by subclasses)
- `write_output(data: list)` — serializes results to JSON with metadata
- `run()` — orchestrates fetch → parse → write with error handling and timing

### HeadlineAgent

Extracts `<h1>`, `<h2>`, `<h3>` and headline-class elements. Captures text content and section/position context. Skips malformed elements with logging.

### ImageAgent

Extracts `<img>` elements. Captures `src`, `alt`, and `title` attributes. Records elements missing `src` with a `null` source field.

### LinksAgent

Extracts `<a>` hyperlink elements. Captures `href`, anchor text, and parent section. Resolves relative URLs to absolute using `urllib.parse.urljoin`.

### MetadataAgent

Extracts page-level metadata: `<title>`, `<meta>` description, section headings, and visible timestamps. Each item stored with type and value.

### OutputWriter

Utility responsible for:
- Constructing the output file path using `{agent_name}_output.json` pattern
- Building the metadata section (agent name, timestamp, target URL, item count)
- Writing valid JSON to the configured output directory

### AgentLogger

A logging wrapper that:
- Prefixes all messages with the agent's unique name
- Records start/end timestamps for each agent execution
- Uses Python's `logging` module with structured format

### Interfaces

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime


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


class BaseAgent(ABC):
    """Abstract base class for all scraping agents."""

    def __init__(self, name: str, target_url: str, output_dir: str):
        self.name = name
        self.target_url = target_url
        self.output_dir = output_dir

    @abstractmethod
    async def parse(self, html: str) -> list[ExtractedItem]:
        """Parse HTML and return extracted items."""
        ...

    async def fetch_page(self) -> str:
        """Fetch the target page HTML content."""
        ...

    async def write_output(self, items: list[ExtractedItem]) -> None:
        """Write extracted items to JSON output file."""
        ...

    async def run(self) -> AgentResult:
        """Execute the full agent pipeline: fetch → parse → write."""
        ...


class ScraperSystem:
    """Top-level orchestrator for all scraping agents."""

    def __init__(self, output_dir: str = "./output"):
        self.output_dir = output_dir
        self.agents: list[BaseAgent] = []

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent. Raises ValueError if name is duplicate."""
        ...

    async def run_all(self) -> list[AgentResult]:
        """Launch all agents concurrently and return results."""
        ...

    def print_summary(self, results: list[AgentResult]) -> None:
        """Print execution summary with success/failure status per agent."""
        ...
```

## Data Models

### Output JSON Structure

Each agent produces a JSON file with this structure:

```json
{
  "metadata": {
    "agent_name": "headline_agent",
    "timestamp": "2024-01-15T10:30:00Z",
    "target_url": "https://www.ynet.co.il/home/0,7340,L-8,00.html",
    "item_count": 25
  },
  "items": [
    {
      "text": "...",
      "section": "...",
      "position": 1
    }
  ]
}
```

### Error Output JSON Structure

When an agent fails to fetch or encounters a fatal error:

```json
{
  "metadata": {
    "agent_name": "headline_agent",
    "timestamp": "2024-01-15T10:30:00Z",
    "target_url": "https://www.ynet.co.il/home/0,7340,L-8,00.html",
    "item_count": 0
  },
  "error": {
    "type": "HTTPError",
    "message": "Failed to fetch page: 503 Service Unavailable",
    "status_code": 503
  },
  "items": []
}
```

## Error Handling

| Scenario | Handler | Behavior |
|----------|---------|----------|
| HTTP fetch failure | `BaseAgent.run()` | Log error, write error output file, return failed `AgentResult` |
| Element parsing error | Agent `parse()` method | Skip element, log warning, continue with remaining elements |
| Missing required attribute | Agent `parse()` method | Record with `null` field value, continue processing |
| Unhandled agent exception | `ScraperSystem.run_all()` | Caught by `asyncio.gather(return_exceptions=True)`, logged, other agents unaffected |
| Output directory missing | `OutputWriter` | Create directory if it doesn't exist |
| JSON serialization error | `OutputWriter` | Log error, attempt simplified output |

## Key Design Decisions

1. **asyncio.gather with return_exceptions=True**: Ensures one agent's exception doesn't cancel others. Each agent's result (or exception) is collected independently.

2. **BeautifulSoup for parsing**: Chosen for its tolerance of malformed HTML, which is common on news sites. Agents use `html.parser` backend (no external C dependencies).

3. **aiohttp for HTTP**: Async HTTP client that integrates naturally with asyncio, supporting concurrent fetches without thread pools.

4. **Dataclasses for data models**: Lightweight, type-safe structures without heavy ORM dependencies. Easy to serialize to JSON via `dataclasses.asdict()`.

5. **Single fetch per agent**: Each agent fetches the page independently. While this means 4 HTTP requests to the same URL, it maintains agent isolation and simplifies the architecture. A shared cache could be added later if needed.

## Testing Strategy

### Unit Tests (Example-Based)
- Verify each agent extracts expected items from known HTML fixtures
- Verify output directory configuration is respected
- Verify specific error scenarios (404, 500, timeout) produce correct error output
- Verify agent registration rejects duplicate names

### Property-Based Tests
- Use `hypothesis` library with minimum 100 iterations per property
- Generate random HTML structures with known elements to test extraction completeness
- Generate random agent names and configurations to test naming and metadata
- Generate random URL paths to test relative URL resolution
- Generate random combinations of succeeding/failing agents to test isolation

### Integration Tests
- Verify concurrent execution with mock HTTP responses
- Verify end-to-end flow produces expected output files
- Verify system handles real-world malformed HTML gracefully

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Agent independence under failure

*For any* set of registered agents where one or more agents raise exceptions, all non-failing agents SHALL still complete their execution and produce their output files.

**Validates: Requirements 1.3, 7.2**

### Property 2: Completion report completeness

*For any* set of registered agents with any combination of success/failure outcomes, the completion summary SHALL contain exactly one status entry per registered agent, correctly classifying each as succeeded or failed.

**Validates: Requirements 1.4, 7.3**

### Property 3: Agent extraction completeness

*For any* HTML page containing elements of an agent's target type (headlines, images, links, or metadata), the agent SHALL extract all valid matching elements from the page.

**Validates: Requirements 2.1, 3.1, 4.1, 5.1**

### Property 4: Extracted item field completeness

*For any* extracted item, the result SHALL contain all required fields for that agent type: headline (text, section), image (url/null, alt_text, title), link (url, anchor_text, parent_section), metadata (type, value).

**Validates: Requirements 2.2, 3.2, 4.2, 5.2**

### Property 5: Resilience to malformed elements

*For any* HTML page containing a mix of valid and malformed elements of an agent's target type, the agent SHALL still extract all valid elements — malformed elements do not prevent extraction of subsequent valid elements.

**Validates: Requirements 2.4, 3.4**

### Property 6: Image elements without source recorded as null

*For any* HTML page containing image elements without a `src` attribute, the Image_Agent SHALL include those elements in its output with a `null` source field rather than skipping them.

**Validates: Requirements 3.4**

### Property 7: Relative URL resolution

*For any* relative URL encountered by the Links_Agent, resolving it against the target page base URL SHALL produce a valid absolute URL that begins with a scheme (http/https).

**Validates: Requirements 4.4**

### Property 8: Output file naming convention

*For any* registered agent with a given name, the system SHALL produce an output file named exactly `{agent_name}_output.json`.

**Validates: Requirements 6.1**

### Property 9: Output metadata section completeness

*For any* agent output file, the JSON SHALL contain a metadata section with all required fields: agent_name, timestamp, target_url, and item_count, where item_count matches the actual number of items in the items array.

**Validates: Requirements 6.3**

### Property 10: JSON output validity (serialization round-trip)

*For any* agent output, the written file content SHALL be valid JSON that can be parsed by `json.loads()` and the deserialized structure SHALL contain both a "metadata" object and an "items" array.

**Validates: Requirements 6.4, 2.3, 3.3, 4.3, 5.3**

### Property 11: Error output on fetch failure

*For any* HTTP error status code or network exception encountered during page fetch, the agent SHALL produce an output file containing the error details (error type and message) alongside an empty items array.

**Validates: Requirements 7.1**

### Property 12: Agent name uniqueness

*For any* set of agents registered with the ScraperSystem, no two agents SHALL share the same name. Attempting to register a duplicate name SHALL raise an error.

**Validates: Requirements 8.1**

### Property 13: Log message agent prefix

*For any* agent with a given name and any log message produced during execution, the formatted log output SHALL contain the agent's unique name as a prefix.

**Validates: Requirements 8.2**

### Property 14: Execution timing recorded

*For any* agent execution (successful or failed), the system SHALL record both a start timestamp and an end timestamp, where end_time >= start_time.

**Validates: Requirements 8.3**
