from __future__ import annotations
import httpx
from app.models.paper import PaperMetadata
from configs.settings import settings

BASE_URL = "https://api.openalex.org/works"


async def search_openalex(topic: str, limit: int = 10) -> list[PaperMetadata]:
    params = {
        "search": topic,
        "per-page": limit,
        "mailto": settings.CROSSREF_MAILTO,
        "select": "id,title,authorships,publication_year,abstract_inverted_index,doi,open_access,cited_by_count,primary_location,keywords",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        items = resp.json().get("results", [])

    papers = []
    for item in items:
        abstract = _reconstruct_abstract(item.get("abstract_inverted_index") or {})
        pdf_url = (item.get("open_access") or {}).get("oa_url")
        authors = [
            a["author"].get("display_name", "")
            for a in item.get("authorships", [])
        ]
        papers.append(PaperMetadata(
            paper_id=f"oa_{item['id'].split('/')[-1]}",
            title=item.get("title", ""),
            authors=authors,
            year=item.get("publication_year"),
            abstract=abstract,
            doi=item.get("doi", "").replace("https://doi.org/", "") if item.get("doi") else None,
            pdf_url=pdf_url,
            source_url=item.get("id"),
            citation_count=item.get("cited_by_count"),
            source="openalex",
            keywords=[k.get("display_label", "") for k in item.get("keywords", [])],
        ))
    return papers


def _reconstruct_abstract(inverted: dict[str, list[int]]) -> str:
    """Reconstruct abstract from OpenAlex inverted index."""
    if not inverted:
        return ""
    word_positions = [(pos, word) for word, positions in inverted.items() for pos in positions]
    word_positions.sort()
    return " ".join(word for _, word in word_positions)
