from __future__ import annotations
import asyncio
import logging

from app.core.state import AgentState
from app.agents.search.sources.semantic_scholar import search_semantic_scholar
from app.agents.search.sources.arxiv import search_arxiv
from app.agents.search.sources.openalex import search_openalex
from app.agents.search.deduplicator import deduplicate
from configs.settings import settings

logger = logging.getLogger(__name__)


async def search_node(state: AgentState) -> dict:
    """Search all configured academic sources and deduplicate results."""
    topic = state["topic"]
    per_source = max(5, settings.MAX_PAPERS_PER_SEARCH // 3)

    results = await asyncio.gather(
        search_semantic_scholar(topic, limit=per_source),
        search_arxiv(topic, limit=per_source),
        search_openalex(topic, limit=per_source),
        return_exceptions=True,
    )

    all_papers = []
    errors = []
    for r in results:
        if isinstance(r, Exception):
            errors.append(str(r))
            logger.warning(f"Search source failed: {r}")
        else:
            all_papers.extend(r)

    deduped = deduplicate(all_papers)
    logger.info(f"Search: found {len(deduped)} unique papers for '{topic}'")

    pipeline = state.get("pipeline", [])
    current_idx = pipeline.index("search_node") if "search_node" in pipeline else -1
    next_step = pipeline[current_idx + 1] if current_idx + 1 < len(pipeline) else "END"

    return {
        "papers": deduped,
        "current_step": next_step,
        "errors": errors,
    }
