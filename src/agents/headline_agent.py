"""Agent specialized in extracting news headlines."""

from bs4 import BeautifulSoup

from src.base_agent import BaseAgent
from src.models import ExtractedItem, HeadlineItem


class HeadlineAgent(BaseAgent):
    """Extracts news headlines from the target page."""

    def __init__(self, target_url: str, output_dir: str, name: str = "headline_agent"):
        super().__init__(name=name, target_url=target_url, output_dir=output_dir)

    async def parse(self, html: str) -> list[ExtractedItem]:
        """Extract all headline elements (h1, h2, h3) from the page."""
        self.logger.info("Parsing headlines...")
        soup = BeautifulSoup(html, "html.parser")
        items: list[ExtractedItem] = []
        position = 0

        # Find all heading elements
        heading_tags = soup.find_all(["h1", "h2", "h3", "h4"])

        for tag in heading_tags:
            try:
                text = tag.get_text(strip=True)
                if not text:
                    continue

                # Determine section from parent or nearest section-like ancestor
                section = self._get_section(tag)
                position += 1

                items.append(HeadlineItem(
                    text=text,
                    section=section,
                    position=position,
                ))
            except Exception as e:
                self.logger.warning(f"Skipping malformed headline element: {e}")
                continue

        self.logger.info(f"Extracted {len(items)} headlines")
        return items

    def _get_section(self, tag) -> str:
        """Determine the section context of a heading element."""
        # Walk up to find a section, article, or div with class/id
        for parent in tag.parents:
            if parent.name in ("section", "article", "nav"):
                section_id = parent.get("id", "") or parent.get("class", [""])[0]
                if section_id:
                    if isinstance(section_id, list):
                        return section_id[0]
                    return section_id
            if parent.name == "div":
                div_class = parent.get("class", [])
                if div_class:
                    return div_class[0] if isinstance(div_class, list) else div_class
        return "unknown"
