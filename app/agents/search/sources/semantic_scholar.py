from __future__ import annotations
import httpx
from app.models.paper import PaperMetadata
from configs.settings import settings

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
FIELDS   = "paperId,title,authors,year,abstract,externalIds,openAccessPdf,citationCount,venue"


async def search_semantic_scholar(topic: str, limit: int = 10) -> list[PaperMetadata]:
    params = {"query": topic, "limit": limit, "fields": FIELDS}
    headers = {}
    if settings.SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = settings.SEMANTIC_SCHOLAR_API_KEY

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(BASE_URL, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json().get("data", [])

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
