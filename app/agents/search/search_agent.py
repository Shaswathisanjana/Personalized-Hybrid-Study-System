from __future__ import annotations
import logging

from app.core.state import AgentState
from app.agents.search.sources.arxiv import search_arxiv
from app.agents.search.deduplicator import deduplicate
from configs.settings import settings

logger = logging.getLogger(__name__)


async def search_node(state: AgentState) -> dict:
    """Search arXiv for papers on the given topic."""
    topic  = state["topic"]
    target = settings.MAX_PAPERS_PER_SEARCH
    errors = []

    try:
        papers = await search_arxiv(topic, limit=target)
        logger.info(f"Search: arXiv returned {len(papers)} papers for '{topic}'")
    except Exception as e:
        logger.warning(f"arXiv search failed: {e}")
        errors.append(f"arXiv search failed: {e}")
        papers = []

    if not papers:
        errors.append(
            "⚠️ arXiv search returned no results. Check your internet connection "
            "or try a different/simpler topic keyword."
        )

    deduped = deduplicate(papers)[:target]
    logger.info(f"Search: {len(deduped)} unique papers found for '{topic}'")

    pipeline    = state.get("pipeline", [])
    current_idx = pipeline.index("search_node") if "search_node" in pipeline else -1
    next_step   = pipeline[current_idx + 1] if current_idx + 1 < len(pipeline) else "END"

    return {
        "papers":       deduped,
        "current_step": next_step,
        "errors":       errors,
    }
