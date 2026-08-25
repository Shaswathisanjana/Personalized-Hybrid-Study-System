from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.graph import research_graph

router = APIRouter(prefix="/research", tags=["Research"])


class ResearchRequest(BaseModel):
    query: str


@router.post("/")
async def start_research(request: ResearchRequest) -> dict:
    """Invoke the full research pipeline synchronously."""
    initial_state = {
        "user_query": request.query,
        "topic": "",
        "intent": "",
        "pipeline": [],
        "papers": [],
        "extractions": [],
        "literature_review": None,
        "gap_analysis": None,
        "novelty_report": None,
        "report": None,
        "citations": None,
        "qa_request": None,
        "qa_response": None,
        "errors": [],
        "current_step": "manager_node",
        "retry_count": 0,
    }
    final_state = await research_graph.ainvoke(initial_state)
    return {
        "status": "success",
        "intent": final_state.get("intent"),
        "papers_found": len(final_state.get("papers", [])),
        "report": final_state.get("report"),
        "errors": final_state.get("errors", []),
    }
