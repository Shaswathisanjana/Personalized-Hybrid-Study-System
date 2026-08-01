"""
Research Agent: topic -> fetch papers -> summarize each -> comparison table.

This is the ONE agent that's fully wired end-to-end for the zeroth review demo.
Everything else (Education Agent, Coding Agent) is future scope — do not build
those now, just reference them in slides.
"""
import asyncio

from backend.services import semantic_scholar, llm, rag
from backend.models import PaperSummary, ResearchResponse


async def run(query: str, max_papers: int = 8) -> ResearchResponse:
    papers = await semantic_scholar.search_papers(query, limit=max_papers)

    if not papers:
        return ResearchResponse(
            topic=query,
            papers=[],
            comparison_table_markdown="No papers found for this topic. Try a broader query.",
        )

    # Summarize all papers concurrently for speed
    summaries = await asyncio.gather(
        *[llm.summarize_paper(p["title"], p["abstract"]) for p in papers]
    )

    enriched = []
    for paper, summary in zip(papers, summaries):
        enriched.append({**paper, "summary": summary})

    table = await llm.build_comparison_table(query, enriched)

    # Persist to the vector store — powers RAG on follow-up questions and the dashboard
    rag.add_papers(query, papers)

    paper_models = [
        PaperSummary(
            title=p["title"],
            authors=p["authors"],
            year=p["year"],
            url=p["url"],
            abstract=p["abstract"],
            summary=p["summary"],
        )
        for p in enriched
    ]

    return ResearchResponse(
        topic=query, papers=paper_models, comparison_table_markdown=table
    )
