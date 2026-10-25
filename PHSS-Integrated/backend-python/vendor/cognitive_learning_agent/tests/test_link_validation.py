"""Tests for link validity and URL deduplication."""

import pytest
from cognitive_learning_agent.discovery.validator import LinkValidator


def test_url_normalization():
    validator = LinkValidator()

    url1 = "https://docs.python.org/3/library/asyncio.html?utm_source=twitter&utm_medium=social"
    url2 = "HTTPS://DOCS.PYTHON.ORG/3/library/asyncio.html/"
    url3 = "https://docs.python.org/3/library/asyncio.html#section-1"

    norm1 = validator.normalize_url(url1)
    norm2 = validator.normalize_url(url2)
    norm3 = validator.normalize_url(url3)

    assert norm1 == "https://docs.python.org/3/library/asyncio.html"
    assert norm2 == "https://docs.python.org/3/library/asyncio.html"
    assert norm3 == "https://docs.python.org/3/library/asyncio.html"


def test_deduplication():
    validator = LinkValidator()
    raw_items = [
        {"url": "https://docs.python.org/3/library/asyncio.html?utm_source=test", "title": "Doc 1"},
        {"url": "https://docs.python.org/3/library/asyncio.html", "title": "Doc 2"},
        {"url": "https://realpython.com/async-io-python/", "title": "Real Python"},
    ]

    # Validate and deduplicate with mock check
    validator.check_link = lambda url: (True, 200, url)
    results = validator.validate_and_deduplicate(raw_items)

    assert len(results) == 2
    urls = [r["url"] for r in results]
    assert "https://docs.python.org/3/library/asyncio.html" in urls
    assert "https://realpython.com/async-io-python" in urls


def test_filter_broken_links():
    validator = LinkValidator()
    raw_items = [
        {"url": "https://docs.python.org/3/library/asyncio.html", "title": "Valid"},
        {"url": "https://example.invalid/404-page-not-found", "title": "Broken"},
    ]

    def mock_check(url):
        if "invalid" in url:
            return False, 404, url
        return True, 200, url

    validator.check_link = mock_check
    results = validator.validate_and_deduplicate(raw_items)

    assert len(results) == 1
    assert results[0]["title"] == "Valid"
