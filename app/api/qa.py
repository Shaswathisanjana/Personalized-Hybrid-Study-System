from __future__ import annotations
from fastapi import APIRouter
from app.models.qa import QARequest
from app.core.graph import research_graph

router = APIRouter(prefix="/qa", tags=["Q&A"])


@router.post("/")
async def ask_question(request: QARequest) -> dict:
    """Ask a question about a previously generated report."""
    state = {
        "user_query": request.question,
        "topic": "",
        "intent": "qa",
        "pipeline": ["qa_node"],
        "papers": [],
        "extractions": [],
        "literature_review": None,
        "gap_analysis": None,
        "novelty_report": None,
        "report": {"report_id": request.report_id},
        "citations": None,
        "qa_request": request.model_dump(),
        "qa_response": None,
        "errors": [],
        "current_step": "qa_node",
        "retry_count": 0,
    }
    final_state = await research_graph.ainvoke(state)
    return {
        "status": "success",
        "qa_response": final_state.get("qa_response"),
    }
