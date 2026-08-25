from __future__ import annotations
import asyncio
import logging

from app.core.state import AgentState
from app.agents.reading.pdf_parser import parse_pdf_with_fallback
from app.agents.reading.extractor import extract_structured_info
from app.agents.reading.embedder import embed_and_store
from app.knowledge_base.chroma_client import KnowledgeBase

logger = logging.getLogger(__name__)
_kb = KnowledgeBase()


async def reading_node(state: AgentState) -> dict:
    """Download PDFs, extract structured info, and store in knowledge base."""
    papers = state.get("papers", [])
    report_id = (state.get("report") or {}).get("report_id", "session_default")

    async def process_one(paper):
        try:
            text, confidence = await parse_pdf_with_fallback(paper)
            extraction = await extract_structured_info(paper, text)
            extraction.extraction_confidence = confidence
            await embed_and_store(_kb, extraction, text, paper, report_id)
            return extraction
        except Exception as e:
            logger.warning(f"Reading: failed for {paper.paper_id}: {e}")
            return None

    tasks = [process_one(p) for p in papers]
    results = await asyncio.gather(*tasks)
    extractions = [r for r in results if r is not None]

    logger.info(f"Reading: extracted {len(extractions)}/{len(papers)} papers")
    pipeline = state.get("pipeline", [])
    idx = pipeline.index("reading_node") if "reading_node" in pipeline else -1
    next_step = pipeline[idx + 1] if idx + 1 < len(pipeline) else "END"

    return {"extractions": extractions, "current_step": next_step}
