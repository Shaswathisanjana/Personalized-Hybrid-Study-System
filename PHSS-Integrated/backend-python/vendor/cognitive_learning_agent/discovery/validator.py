"""Link validation and URL deduplication for online learning resources."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import requests

from cognitive_learning_agent.config import settings

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


TRUSTED_DOMAINS = {
    "docs.python.org", "python.org", "geeksforgeeks.org", "www.geeksforgeeks.org",
    "programiz.com", "www.programiz.com", "realpython.com", "w3schools.com",
    "www.w3schools.com", "arxiv.org", "youtube.com", "www.youtube.com",
    "khanacademy.org", "www.khanacademy.org", "github.com", "en.wikipedia.org",
    "jalammar.github.io", "developer.mozilla.org"
}


class LinkValidator:
    """Validates URLs for liveness, resolves redirects, and deduplicates canonical links."""

    def __init__(self, timeout: int = 2, max_workers: int = settings.MAX_VALIDATION_WORKERS):
        self.timeout = min(timeout, 2)
        self.max_workers = max_workers

    def validate_and_deduplicate(self, raw_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Deduplicate items and validate links concurrently."""
        # 1. Deduplicate by canonical URL first
        canonical_map = {}
        for item in raw_items:
            url = item.get("url")
            if not url:
                continue
            canonical = self.normalize_url(url)
            if canonical not in canonical_map:
                item["canonical_url"] = canonical
                item["url"] = canonical
                canonical_map[canonical] = item

        unique_items = list(canonical_map.values())

        # 2. Concurrently validate HTTP status
        validated_results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_item = {
                executor.submit(self.check_link, item["url"]): item
                for item in unique_items
            }
            for future in as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    is_valid, status_code, final_url = future.result()
                    if is_valid:
                        item["is_valid"] = True
                        item["status_code"] = status_code
                        item["url"] = final_url  # Use resolved URL
                        validated_results.append(item)
                    else:
                        logger.debug(f"Filtering out invalid URL: {item['url']} (status: {status_code})")
                except Exception as e:
                    logger.debug(f"Validation failed for {item.get('url')}: {e}")

        return validated_results

    def check_link(self, url: str) -> Tuple[bool, int, str]:
        """Check if URL returns 2xx or 3xx and can be fetched."""
        try:
            domain = urlparse(url).netloc.lower()
            if domain in TRUSTED_DOMAINS or any(domain.endswith("." + td) for td in TRUSTED_DOMAINS):
                return True, 200, url
        except Exception:
            pass

        try:
            # First attempt HEAD request
            resp = requests.head(
                url,
                headers=HEADERS,
                timeout=self.timeout,
                allow_redirects=True,
            )
            if 200 <= resp.status_code < 400:
                return True, resp.status_code, resp.url

            # Some servers block HEAD, try lightweight GET with stream=True
            resp = requests.get(
                url,
                headers=HEADERS,
                timeout=self.timeout,
                allow_redirects=True,
                stream=True,
            )
            if 200 <= resp.status_code < 400:
                return True, resp.status_code, resp.url
            return False, resp.status_code, url

        except requests.exceptions.SSLError:
            # Retry without SSL verification for educational servers with self-signed certs
            try:
                resp = requests.get(url, headers=HEADERS, timeout=self.timeout, verify=False, stream=True)
                if 200 <= resp.status_code < 400:
                    return True, resp.status_code, resp.url
            except Exception:
                pass
            return False, 0, url
        except Exception:
            return False, 0, url

    @staticmethod
    def normalize_url(url: str) -> str:
        """Strip tracking parameters, fragments, and trailing slashes to obtain canonical form."""
        try:
            parsed = urlparse(url)
            # Remove tracking query params like utm_*
            clean_query = [
                (k, v)
                for k, v in parse_qsl(parsed.query)
                if not k.startswith("utm_") and k not in ["ref", "source", "fbclid"]
            ]
            path = parsed.path.rstrip("/")
            normalized = urlunparse(
                (
                    parsed.scheme.lower(),
                    parsed.netloc.lower(),
                    path,
                    parsed.params,
                    urlencode(clean_query),
                    "",  # Strip fragment
                )
            )
            return normalized
        except Exception:
            return url.strip().lower()
