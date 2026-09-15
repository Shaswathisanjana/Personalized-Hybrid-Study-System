from __future__ import annotations
import asyncio
import logging

from app.core.state import AgentState
from app.agents.reading.pdf_parser import parse_pdf_with_fallback
from app.agents.reading.extractor import extract_structured_info
from app.agents.reading.embedder import embed_and_store
from app.knowledge_base.chroma_client import KnowledgeBase
from app.models.paper import PaperExtraction

logger = logging.getLogger(__name__)
_kb = KnowledgeBase()


def _metadata_fallback(paper) -> PaperExtraction:
    """Build a minimal PaperExtraction from abstract/metadata (no LLM needed)."""
    pid      = paper.get("paper_id") if isinstance(paper, dict) else paper.paper_id
    title    = paper.get("title")    if isinstance(paper, dict) else paper.title
    authors  = paper.get("authors")  if isinstance(paper, dict) else paper.authors
    year     = paper.get("year")     if isinstance(paper, dict) else paper.year
    doi      = paper.get("doi")      if isinstance(paper, dict) else paper.doi
    abstract = paper.get("abstract") if isinstance(paper, dict) else paper.abstract
    keywords = paper.get("keywords", []) if isinstance(paper, dict) else paper.keywords
    return PaperExtraction(
        paper_id=pid,
        title=title or "",
        authors=authors or [],
        year=year,
        doi=doi,
        problem_statement=(abstract or "")[:500] or None,
        methodology="Not extracted — abstract only (LLM rate limited)",
        results_summary="Not extracted — abstract only (LLM rate limited)",
        keywords=keywords,
        extraction_confidence=0.1,
    )


async def reading_node(state: AgentState) -> dict:
    """Download PDFs, extract structured info, and store in knowledge base."""
    papers    = state.get("papers", [])
    report_id = (state.get("report") or {}).get("report_id", "session_default")
    read_errors: list[str] = []

    async def process_one(paper):
        pid = paper.get("paper_id") if isinstance(paper, dict) else paper.paper_id
        # Retry up to 3 times on 429 / quota errors with exponential backoff
        for attempt in range(3):
            try:
                text, confidence = await parse_pdf_with_fallback(paper)
                extraction = await extract_structured_info(paper, text)
                extraction.extraction_confidence = confidence
                await embed_and_store(_kb, extraction, text, paper, report_id)
                return extraction
            except Exception as e:
                msg = str(e)
                is_rate_limit = "429" in msg or "quota" in msg.lower() or "ResourceExhausted" in msg
                if is_rate_limit and attempt < 2:
                    wait = 20 * (2 ** attempt)   # 20s then 40s
                    logger.warning(
                        "Reading: rate limit for %s, retrying in %ds (attempt %d/3)",
                        pid, wait, attempt + 1
                    )
                    await asyncio.sleep(wait)
                    continue
                err_msg = f"Reading: failed for {pid}: {type(e).__name__}: {e}"
                logger.warning(err_msg)
                read_errors.append(err_msg)
                return None

    # Sequential with 8s gap — stays under Gemini's 10 req/min free tier limit
    extractions = []
    for i, paper in enumerate(papers):
        result = await process_one(paper)
        if result is not None:
            extractions.append(result)
        if i < len(papers) - 1:
            await asyncio.sleep(8)

    # If ALL LLM extractions failed, fall back to abstract-only extractions so
    # downstream agents still produce a real report instead of hallucinating from nothing.
    if not extractions and papers:
        logger.warning(
            "Reading: all LLM extractions failed — using abstract-only fallbacks for %d papers",
            len(papers)
        )
        read_errors.append(
            "⚠️ LLM extraction failed for all papers (Gemini rate limit). "
            "Report content will be based on paper abstracts only."
        )
        for paper in papers:
            fb = _metadata_fallback(paper)
            await embed_and_store(_kb, fb, fb.problem_statement or "", paper, report_id)
            extractions.append(fb)

    logger.info(f"Reading: extracted {len(extractions)}/{len(papers)} papers")
    pipeline  = state.get("pipeline", [])
    idx       = pipeline.index("reading_node") if "reading_node" in pipeline else -1
    next_step = pipeline[idx + 1] if idx + 1 < len(pipeline) else "END"

    return {"extractions": extractions, "current_step": next_step, "errors": read_errors}
