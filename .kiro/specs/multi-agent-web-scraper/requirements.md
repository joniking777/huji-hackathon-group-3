# Requirements Document

## Introduction

A Python-based concurrent multi-agent web scraping system targeting the Ynet homepage. Multiple specialized agents run simultaneously, each focusing on a different content area of the page (headlines, images/graphics, article links, metadata). Each agent independently extracts its assigned content and writes results to its own JSON output file. The system demonstrates parallel agent behavior through individually observable outputs.

## Glossary

- **Scraper_System**: The top-level Python application that initializes, orchestrates, and manages the lifecycle of all scraping agents
- **Agent**: An independent concurrent unit of execution that scrapes a specific content type from the target page
- **Headline_Agent**: An Agent specialized in extracting news headlines and their associated text
- **Image_Agent**: An Agent specialized in extracting image URLs, alt text, and graphic titles
- **Links_Agent**: An Agent specialized in extracting article links, their URLs, and anchor text
- **Metadata_Agent**: An Agent specialized in extracting page metadata such as timestamps, section names, and structural information
- **Target_Page**: The Ynet homepage at https://www.ynet.co.il/home/0,7340,L-8,00.html
- **Output_File**: A JSON file produced by a single Agent containing its extracted data
- **Agent_Registry**: The component that tracks all registered agents and their execution status

## Requirements

### Requirement 1: Concurrent Agent Execution

**User Story:** As a developer, I want multiple scraping agents to run concurrently, so that I can observe how parallel agents behave independently.

#### Acceptance Criteria

1. WHEN the Scraper_System is started, THE Scraper_System SHALL launch all registered agents concurrently using Python asyncio.
2. THE Scraper_System SHALL support a minimum of four concurrent agents running simultaneously.
3. WHILE agents are executing, THE Scraper_System SHALL allow each Agent to operate independently without blocking other agents.
4. WHEN all agents have completed execution, THE Scraper_System SHALL report the completion status of each Agent.

### Requirement 2: Headline Extraction

**User Story:** As a developer, I want a dedicated agent to extract headlines from the Ynet homepage, so that I can examine headline data in isolation.

#### Acceptance Criteria

1. WHEN the Headline_Agent is launched, THE Headline_Agent SHALL fetch the Target_Page and extract all news headline text elements.
2. THE Headline_Agent SHALL capture the headline text content and its position or section on the page for each extracted headline.
3. WHEN extraction is complete, THE Headline_Agent SHALL write results to its dedicated Output_File in JSON format.
4. IF the Headline_Agent encounters a parsing error for a specific element, THEN THE Headline_Agent SHALL skip that element, log the error, and continue processing remaining elements.

### Requirement 3: Image and Graphics Extraction

**User Story:** As a developer, I want a dedicated agent to extract image and graphic information, so that I can analyze visual content metadata separately.

#### Acceptance Criteria

1. WHEN the Image_Agent is launched, THE Image_Agent SHALL fetch the Target_Page and extract all image elements and their associated metadata.
2. THE Image_Agent SHALL capture the image URL, alt text, and title attribute for each extracted image element.
3. WHEN extraction is complete, THE Image_Agent SHALL write results to its dedicated Output_File in JSON format.
4. IF the Image_Agent encounters an image element without a source URL, THEN THE Image_Agent SHALL record the element with a null source field and continue processing.

### Requirement 4: Article Links Extraction

**User Story:** As a developer, I want a dedicated agent to extract article links, so that I can review the link structure of the page independently.

#### Acceptance Criteria

1. WHEN the Links_Agent is launched, THE Links_Agent SHALL fetch the Target_Page and extract all article hyperlink elements.
2. THE Links_Agent SHALL capture the link URL, anchor text, and parent section for each extracted hyperlink.
3. WHEN extraction is complete, THE Links_Agent SHALL write results to its dedicated Output_File in JSON format.
4. IF the Links_Agent encounters a relative URL, THEN THE Links_Agent SHALL resolve the relative URL to an absolute URL before recording.

### Requirement 5: Page Metadata Extraction

**User Story:** As a developer, I want a dedicated agent to extract page metadata, so that I can understand the structural and temporal context of the page.

#### Acceptance Criteria

1. WHEN the Metadata_Agent is launched, THE Metadata_Agent SHALL fetch the Target_Page and extract page-level metadata including page title, meta description, section names, and any visible timestamps.
2. THE Metadata_Agent SHALL capture each metadata item with its type and value.
3. WHEN extraction is complete, THE Metadata_Agent SHALL write results to its dedicated Output_File in JSON format.

### Requirement 6: JSON Output Format

**User Story:** As a developer, I want each agent to produce a structured JSON file, so that I can compare and analyze agent outputs individually.

#### Acceptance Criteria

1. THE Scraper_System SHALL produce one Output_File per Agent, named with the pattern `{agent_name}_output.json`.
2. THE Scraper_System SHALL write all Output_Files to a configurable output directory.
3. WHEN an Agent writes its Output_File, THE Agent SHALL include a metadata section containing the agent name, extraction timestamp, target URL, and item count.
4. THE Scraper_System SHALL produce valid JSON in each Output_File that is parseable by standard JSON libraries.

### Requirement 7: Error Handling and Resilience

**User Story:** As a developer, I want the system to handle errors gracefully, so that one agent's failure does not affect other agents.

#### Acceptance Criteria

1. IF an Agent fails to fetch the Target_Page, THEN THE Agent SHALL log the error with the HTTP status code or exception details and produce an Output_File containing the error information.
2. IF an Agent raises an unhandled exception, THEN THE Scraper_System SHALL catch the exception, log the failure, and allow remaining agents to continue execution.
3. WHEN the Scraper_System completes execution, THE Scraper_System SHALL produce a summary indicating which agents succeeded and which agents failed.

### Requirement 8: Agent Identification and Observability

**User Story:** As a developer, I want to clearly identify which agent produced which output, so that I can trace behavior back to individual agents.

#### Acceptance Criteria

1. THE Scraper_System SHALL assign a unique name to each Agent at registration time.
2. WHEN an Agent logs a message, THE Agent SHALL prefix the log message with its unique agent name.
3. THE Scraper_System SHALL log the start time and end time of each Agent's execution to enable performance comparison between agents.
