"""Agent specialized in extracting article links."""

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from src.base_agent import BaseAgent
from src.models import ExtractedItem, LinkItem


class LinksAgent(BaseAgent):
    """Extracts hyperlink elements from the target page."""

    def __init__(self, target_url: str, output_dir: str, name: str = "links_agent"):
        super().__init__(name=name, target_url=target_url, output_dir=output_dir)

    async def parse(self, html: str) -> list[ExtractedItem]:
        """Extract all hyperlink elements from the page."""
        self.logger.info("Parsing links...")
        soup = BeautifulSoup(html, "html.parser")
        items: list[ExtractedItem] = []

        a_tags = soup.find_all("a", href=True)

        for tag in a_tags:
            try:
                href = tag.get("href", "")
                anchor_text = tag.get_text(strip=True)

                # Skip empty or javascript links
                if not href or href.startswith("javascript:") or href == "#":
                    continue

                # Resolve relative URLs to absolute
                absolute_url = urljoin(self.target_url, href)

                # Determine parent section
                parent_section = self._get_parent_section(tag)

                items.append(LinkItem(
                    url=absolute_url,
                    anchor_text=anchor_text,
                    parent_section=parent_section,
                ))
            except Exception as e:
                self.logger.warning(f"Skipping malformed link element: {e}")
                continue

        self.logger.info(f"Extracted {len(items)} links")
        return items

    def _get_parent_section(self, tag) -> str:
        """Determine the parent section of a link element."""
        for parent in tag.parents:
            if parent.name in ("section", "article", "nav", "header", "footer"):
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
