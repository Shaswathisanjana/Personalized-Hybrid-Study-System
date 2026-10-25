"""Web page metadata and content extraction using Requests + BeautifulSoup."""

import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

from cognitive_learning_agent.models.schemas import LearningFormat

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class PageExtractor:
    """Extracts titles, descriptions, format tags, and read-time estimates from online resources."""

    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def extract_metadata(self, url: str, initial_title: str = "", initial_snippet: str = "") -> Dict[str, Any]:
        """Fetch page metadata with fallback to initial search snippets."""
        domain = self._extract_domain(url)
        detected_format = self._detect_format_from_url(url)

        meta = {
            "title": initial_title.strip() if initial_title else domain,
            "description": initial_snippet.strip() if initial_snippet else "",
            "domain": domain,
            "format": detected_format,
            "word_count": 500,
            "estimated_minutes": 10 if detected_format != LearningFormat.VIDEO else 15,
        }

        # If it's a known video domain or we already have high-quality search metadata, avoid blocking HTML downloads
        if detected_format == LearningFormat.VIDEO or (initial_title and initial_snippet and len(initial_snippet) > 20):
            return meta

        try:
            resp = requests.get(
                url,
                headers=DEFAULT_HEADERS,
                timeout=self.timeout,
                allow_redirects=True,
                stream=True,
            )
            # Only process HTML
            content_type = resp.headers.get("content-type", "").lower()
            if "text/html" not in content_type:
                return meta

            # Read first 128KB to extract metadata efficiently
            content_chunk = resp.raw.read(131072, decode_content=True)
            soup = BeautifulSoup(content_chunk, "html.parser")

            # Extract title
            title = None
            if soup.find("meta", property="og:title"):
                title = soup.find("meta", property="og:title").get("content")
            elif soup.title and soup.title.string:
                title = soup.title.string.strip()
            elif soup.find("h1"):
                title = soup.find("h1").get_text().strip()

            if title:
                meta["title"] = title

            # Extract description
            desc = None
            if soup.find("meta", property="og:description"):
                desc = soup.find("meta", property="og:description").get("content")
            elif soup.find("meta", attrs={"name": "description"}):
                desc = soup.find("meta", attrs={"name": "description"}).get("content")

            if desc:
                meta["description"] = desc.strip()

            # Estimate word count & reading time
            text = soup.get_text()
            words = len(text.split())
            if words > 100:
                meta["word_count"] = words
                # Average reading speed: 200 words per minute
                meta["estimated_minutes"] = max(3, min(60, round(words / 200)))

        except Exception as e:
            logger.debug(f"Page extraction failed for {url}: {e}")

        return meta

    @staticmethod
    def _extract_domain(url: str) -> str:
        try:
            return urlparse(url).netloc.replace("www.", "")
        except Exception:
            return "online-resource"

    @staticmethod
    def _detect_format_from_url(url: str) -> LearningFormat:
        u_lower = url.lower()
        if any(v in u_lower for v in ["youtube.com", "youtu.be", "vimeo.com", "/video/"]):
            return LearningFormat.VIDEO
        if any(d in u_lower for d in ["docs.", "documentation", "readthedocs", "/docs/", "devdocs.io"]):
            return LearningFormat.DOCUMENTATION
        if any(i in u_lower for i in ["colab.research.google", "replit.com", "codepen.io", "observablehq.com"]):
            return LearningFormat.INTERACTIVE
        if any(p in u_lower for p in ["leetcode.com", "hackerrank.com", "exercism.org", "codewars.com"]):
            return LearningFormat.PRACTICE
        if any(z in u_lower for z in ["jalammar.github.io", "visualgo.net", "distill.pub", "visualization"]):
            return LearningFormat.VISUALIZATION
        return LearningFormat.DOCUMENTATION
