# Implementation Tasks

## Task 1: Project Setup and Dependencies

- [x] Create project structure with `src/` directory and `main.py` entry point
- [x] Create `requirements.txt` with dependencies: `aiohttp`, `beautifulsoup4`, `aiofiles`
- [x] Create `src/__init__.py` package file
- [x] Create `src/models.py` with dataclass definitions (`AgentResult`, `OutputMetadata`, `ExtractedItem`, `HeadlineItem`, `ImageItem`, `LinkItem`, `MetadataItem`)

**Requirements:** R1, R6

## Task 2: BaseAgent Abstract Class and AgentLogger

- [x] Create `src/base_agent.py` with `BaseAgent` abstract class
- [x] Implement `fetch_page()` method using `aiohttp` with error handling
- [x] Implement `write_output()` method that writes JSON with metadata section
- [x] Implement `run()` method orchestrating fetch → parse → write with timing
- [x] Create `src/logger.py` with `AgentLogger` class that prefixes log messages with agent name
- [x] Integrate logger into `BaseAgent` to log start/end times

**Requirements:** R1.3, R6.1, R6.2, R6.3, R6.4, R7.1, R8.2, R8.3

## Task 3: HeadlineAgent Implementation

- [x] Create `src/agents/headline_agent.py` with `HeadlineAgent` class extending `BaseAgent`
- [x] Implement `parse()` method to extract `<h1>`, `<h2>`, `<h3>` and headline-class elements
- [x] Capture text content and section/position for each headline
- [x] Handle parsing errors gracefully: skip malformed elements, log warning, continue

**Requirements:** R2.1, R2.2, R2.3, R2.4

## Task 4: ImageAgent Implementation

- [x] Create `src/agents/image_agent.py` with `ImageAgent` class extending `BaseAgent`
- [x] Implement `parse()` method to extract all `<img>` elements
- [x] Capture `src`, `alt`, and `title` attributes for each image
- [x] Record images without `src` attribute with `null` source field

**Requirements:** R3.1, R3.2, R3.3, R3.4

## Task 5: LinksAgent Implementation

- [x] Create `src/agents/links_agent.py` with `LinksAgent` class extending `BaseAgent`
- [x] Implement `parse()` method to extract all `<a>` hyperlink elements
- [x] Capture `href`, anchor text, and parent section for each link
- [x] Resolve relative URLs to absolute using `urllib.parse.urljoin`

**Requirements:** R4.1, R4.2, R4.3, R4.4

## Task 6: MetadataAgent Implementation

- [x] Create `src/agents/metadata_agent.py` with `MetadataAgent` class extending `BaseAgent`
- [x] Implement `parse()` method to extract `<title>`, `<meta>` description, section headings, and visible timestamps
- [x] Store each metadata item with its type and value

**Requirements:** R5.1, R5.2, R5.3

## Task 7: ScraperSystem Orchestrator

- [x] Create `src/scraper_system.py` with `ScraperSystem` class
- [x] Implement `register_agent()` with duplicate name validation (raise `ValueError`)
- [x] Implement `run_all()` using `asyncio.gather(return_exceptions=True)` for concurrent execution
- [x] Implement `print_summary()` to report success/failure status per agent
- [x] Ensure output directory is created if it doesn't exist

**Requirements:** R1.1, R1.2, R1.3, R1.4, R7.2, R7.3, R8.1

## Task 8: Main Entry Point and Configuration

- [x] Create `main.py` that instantiates `ScraperSystem` with configurable output directory
- [x] Register all four agents (Headline, Image, Links, Metadata) with unique names
- [x] Set target URL to `https://www.ynet.co.il/home/0,7340,L-8,00.html`
- [x] Run the system with `asyncio.run()` and print the summary
- [x] Create `src/agents/__init__.py` to export all agent classes

**Requirements:** R1.1, R1.2, R8.1
