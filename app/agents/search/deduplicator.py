from __future__ import annotations
from app.models.paper import PaperMetadata


def deduplicate(papers: list[PaperMetadata]) -> list[PaperMetadata]:
    """Remove duplicate papers by DOI (preferred) then by normalised title."""
    seen_doi: set[str] = set()
    seen_title: set[str] = set()
    result: list[PaperMetadata] = []

    for p in papers:
        if p.doi:
            key = p.doi.lower().strip()
            if key in seen_doi:
                continue
            seen_doi.add(key)
        else:
            title_key = _normalise(p.title)
            if title_key in seen_title:
                continue
            seen_title.add(title_key)
        result.append(p)

    return result


def _normalise(text: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]", "", text.lower())
