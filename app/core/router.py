from __future__ import annotations
from langgraph.graph import END
from app.core.state import AgentState
import logging

logger = logging.getLogger(__name__)

INTENT_TO_PIPELINE: dict[str, list[str]] = {
    "search_only":  ["search_node"],
    "read_paper":   ["search_node", "reading_node"],
    "lit_review":   ["search_node", "reading_node", "analysis_node",
                     "writing_node", "citation_node"],
    "gap_analysis": ["search_node", "reading_node", "analysis_node",
                     "writing_node", "citation_node"],
    "novelty":      ["search_node", "reading_node", "analysis_node",
                     "writing_node", "citation_node"],
    "full_report":  ["search_node", "reading_node", "analysis_node",
                     "writing_node", "citation_node"],
    "qa":           ["qa_node"],
}


def route_from_manager(state: AgentState) -> str:
    """Conditional edge: manager → first pipeline node."""
    pipeline = state.get("pipeline", [])
    if not pipeline:
        return "error_node"
    return pipeline[0]


def route_next(state: AgentState) -> str:
    """Advance to the next node in the pipeline, or END."""
    pipeline = state.get("pipeline", [])
    current = state.get("current_step", "")
    if state.get("errors") and state.get("retry_count", 0) >= 3:
        return "error_node"
    try:
        idx = pipeline.index(current)
        return pipeline[idx + 1]
    except (ValueError, IndexError):
        return END
