from __future__ import annotations
import asyncio
import logging
import httpx
from app.models.paper import PaperMetadata
from configs.settings import settings

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS   = "paperId,title,authors,year,abstract,externalIds,openAccessPdf,citationCount,venue"

logger = logging.getLogger(__name__)

_MAX_RETRIES   = 4
_RETRY_BACKOFF = 5.0   # seconds; doubles each attempt (5s, 10s, 20s)


async def search_semantic_scholar(topic: str, limit: int = 10) -> list[PaperMetadata]:
    params = {"query": topic, "limit": limit, "fields": FIELDS}
    headers = {}
    if settings.SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = settings.SEMANTIC_SCHOLAR_API_KEY

    last_exc: Exception | None = None
    async with httpx.AsyncClient(timeout=30) as client:
        for attempt in range(_MAX_RETRIES):
            try:
                resp = await client.get(BASE_URL, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json().get("data", [])
                break  # success
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                status = exc.response.status_code
                # Retry on both 429 (rate limit) and 5xx (server errors)
                is_retryable = status == 429 or status >= 500
                if is_retryable and attempt < _MAX_RETRIES - 1:
                    wait = _RETRY_BACKOFF * (2 ** attempt)
                    logger.warning(
                        f"Semantic Scholar attempt {attempt + 1}/{_MAX_RETRIES} failed "
                        f"(HTTP {status}). Retrying in {wait:.0f}s…"
                    )
                    await asyncio.sleep(wait)
                else:
                    raise
            except httpx.TransportError as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    wait = _RETRY_BACKOFF * (2 ** attempt)
                    logger.warning(
                        f"Semantic Scholar attempt {attempt + 1}/{_MAX_RETRIES} transport error "
                        f"({exc}). Retrying in {wait:.0f}s…"
                    )
                    await asyncio.sleep(wait)
                else:
                    raise
        else:
            raise last_exc  # type: ignore[misc]

    papers = []
    for item in data:
        doi = (item.get("externalIds") or {}).get("DOI")
        pdf = (item.get("openAccessPdf") or {}).get("url")
        papers.append(PaperMetadata(
            paper_id=f"ss_{item['paperId']}",
            title=item.get("title", ""),
            authors=[a["name"] for a in item.get("authors", [])],
            year=item.get("year"),
            abstract=item.get("abstract"),
            doi=doi,
            pdf_url=pdf,
            citation_count=item.get("citationCount"),
            source="semantic_scholar",
            venue=item.get("venue"),
        ))
    return papers
