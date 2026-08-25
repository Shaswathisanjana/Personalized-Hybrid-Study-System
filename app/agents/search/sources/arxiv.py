from __future__ import annotations
import asyncio
import arxiv as arxiv_lib
from app.models.paper import PaperMetadata


async def search_arxiv(topic: str, limit: int = 10) -> list[PaperMetadata]:
    """Search arXiv using the arxiv Python library (sync, run in executor)."""
    loop = asyncio.get_event_loop()

    def _sync_search():
        search = arxiv_lib.Search(
            query=topic,
            max_results=limit,
            sort_by=arxiv_lib.SortCriterion.Relevance,
        )
        client = arxiv_lib.Client()
        return list(client.results(search))

    results = await loop.run_in_executor(None, _sync_search)

    papers = []
    for r in results:
        arxiv_id = r.entry_id.split("/")[-1]
        papers.append(PaperMetadata(
            paper_id=f"arxiv_{arxiv_id}",
            title=r.title,
            authors=[str(a) for a in r.authors],
            year=r.published.year if r.published else None,
            abstract=r.summary,
            doi=r.doi,
            pdf_url=r.pdf_url,
            source_url=r.entry_id,
            source="arxiv",
            keywords=r.categories,
        ))
    return papers
