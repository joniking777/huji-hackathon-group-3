"""Agent specialized in extracting page metadata."""

from bs4 import BeautifulSoup

from src.base_agent import BaseAgent
from src.models import ExtractedItem, MetadataItem


class MetadataAgent(BaseAgent):
    """Extracts page-level metadata from the target page."""

    def __init__(self, target_url: str, output_dir: str, name: str = "metadata_agent"):
        super().__init__(name=name, target_url=target_url, output_dir=output_dir)

    async def parse(self, html: str) -> list[ExtractedItem]:
        """Extract page metadata: title, meta tags, section names, timestamps."""
        self.logger.info("Parsing metadata...")
        soup = BeautifulSoup(html, "html.parser")
        items: list[ExtractedItem] = []

        # Page title
        title_tag = soup.find("title")
        if title_tag:
            items.append(MetadataItem(
                type="page_title",
                value=title_tag.get_text(strip=True),
            ))

        # Meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            items.append(MetadataItem(
                type="meta_description",
                value=meta_desc["content"],
            ))

        # Meta keywords
        meta_keywords = soup.find("meta", attrs={"name": "keywords"})
        if meta_keywords and meta_keywords.get("content"):
            items.append(MetadataItem(
                type="meta_keywords",
                value=meta_keywords["content"],
            ))

        # Open Graph metadata
        og_tags = soup.find_all("meta", attrs={"property": lambda x: x and x.startswith("og:")})
        for og in og_tags:
            prop = og.get("property", "")
            content = og.get("content", "")
            if content:
                items.append(MetadataItem(
                    type=f"og_{prop.replace('og:', '')}",
                    value=content,
                ))

        # Section headings (top-level structure)
        sections = soup.find_all(["section", "nav"])
        for section in sections:
            section_id = section.get("id", "")
            section_class = section.get("class", [])
            label = section_id or (section_class[0] if section_class else "")
            if label:
                items.append(MetadataItem(
                    type="section",
                    value=label if isinstance(label, str) else label[0],
                ))

        # Visible timestamps (time elements)
        time_tags = soup.find_all("time")
        for time_tag in time_tags:
            datetime_attr = time_tag.get("datetime", "")
            text = time_tag.get_text(strip=True)
            value = datetime_attr or text
            if value:
                items.append(MetadataItem(
                    type="timestamp",
                    value=value,
                ))

        self.logger.info(f"Extracted {len(items)} metadata items")
        return items
