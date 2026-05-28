"""Agent specialized in extracting images and graphics."""

from bs4 import BeautifulSoup

from src.base_agent import BaseAgent
from src.models import ExtractedItem, ImageItem


class ImageAgent(BaseAgent):
    """Extracts image elements and their metadata from the target page."""

    def __init__(self, target_url: str, output_dir: str, name: str = "image_agent"):
        super().__init__(name=name, target_url=target_url, output_dir=output_dir)

    async def parse(self, html: str) -> list[ExtractedItem]:
        """Extract all image elements from the page."""
        self.logger.info("Parsing images...")
        soup = BeautifulSoup(html, "html.parser")
        items: list[ExtractedItem] = []

        img_tags = soup.find_all("img")

        for tag in img_tags:
            try:
                # src can be None if the attribute is missing
                src = tag.get("src") or tag.get("data-src")
                alt_text = tag.get("alt", "")
                title = tag.get("title", "")

                items.append(ImageItem(
                    url=src,  # Will be None if no src attribute
                    alt_text=alt_text,
                    title=title,
                ))
            except Exception as e:
                self.logger.warning(f"Skipping malformed image element: {e}")
                continue

        self.logger.info(f"Extracted {len(items)} images")
        return items
