"""API routes for research execution and lightweight admin data."""
from datetime import datetime, timezone
import logging
import time
import uuid

from fastapi import APIRouter, HTTPException

from app.agents.workflow import research_graph
from app.api.models import FeedbackRequest, HealthCheck, ResearchRequest, ResearchResponse, SystemStats
from app.core.config import settings
from app.core.runtime_store import runtime_store

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/research", response_model=ResearchResponse)
async def execute_research(request: ResearchRequest):
    """Execute the research workflow."""
    thread_id = request.thread_id or str(uuid.uuid4())
    start_time = time.time()
    history_messages = [message.model_dump() for message in request.messages]

    try:
        config = {"configurable": {"thread_id": thread_id}}
        inputs = {
            "messages": history_messages,
            "query": request.query,
            "thread_id": thread_id,
            "selected_model": request.model,
            "api_key": request.api_key,
            "user_feedback": request.user_feedback or "",
            "revision_count": 0,
            "approved": not settings.ENABLE_HUMAN_REVIEW,
            "start_time": start_time,
        }

        logger.info("Starting research for thread %s", thread_id)
        final_state = await research_graph.ainvoke(inputs, config=config)
        execution_time = time.time() - start_time

        awaiting_review = (
            settings.ENABLE_HUMAN_REVIEW
            and final_state.get("current_step") == "review"
            and not final_state.get("approved", False)
        )
        status = "awaiting_review" if awaiting_review else "completed"

        runtime_store.save_result(
            {
                "thread_id": thread_id,
                "query": request.query,
                "status": status,
                "intent": final_state.get("intent", "UNKNOWN"),
                "final_report": final_state.get("final_report", ""),
                "sources": final_state.get("all_sources", []),
                "citations": final_state.get("citations", []),
                "execution_time": execution_time,
                "created_at": datetime.now(timezone.utc),
            }
        )

        return ResearchResponse(
            thread_id=thread_id,
            status=status,
            report=final_state.get("final_report", ""),
            citations=final_state.get("citations", []),
            sources=final_state.get("all_sources", []),
            execution_time=execution_time,
        )
    except Exception as exc:
        logger.error("Research failed: %s", exc, exc_info=True)
        runtime_store.save_result(
            {
                "thread_id": thread_id,
                "query": request.query,
                "status": "failed",
                "intent": "UNKNOWN",
                "final_report": "",
                "sources": [],
                "citations": [],
                "execution_time": time.time() - start_time,
                "created_at": datetime.now(timezone.utc),
            }
        )
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/research/{thread_id}", response_model=ResearchResponse)
def get_research_result(thread_id: str):
    """Retrieve a research result by thread ID."""
    query = runtime_store.get_result(thread_id)
    if not query:
        raise HTTPException(status_code=404, detail="Research not found")

    return ResearchResponse(
        thread_id=query["thread_id"],
        status=query["status"],
        report=query.get("final_report"),
        citations=query.get("citations", []),
        sources=query.get("sources", []),
        execution_time=query.get("execution_time"),
    )


@router.post("/research/{thread_id}/feedback", response_model=ResearchResponse)
async def submit_feedback(thread_id: str, request: FeedbackRequest):
    """Resume workflow with human feedback when review mode is enabled."""
    if not settings.ENABLE_HUMAN_REVIEW:
        raise HTTPException(status_code=400, detail="Human review mode is disabled")

    config = {"configurable": {"thread_id": thread_id}}
    research_graph.update_state(
        config,
        {"user_feedback": request.feedback, "approved": request.approved},
    )
    final_state = await research_graph.ainvoke(None, config=config)

    existing = runtime_store.get_result(thread_id)
    execution_time = existing.get("execution_time") if existing else None
    runtime_store.save_result(
        {
            "thread_id": thread_id,
            "query": existing.get("query", "") if existing else "",
            "status": "completed" if final_state.get("approved") else "awaiting_review",
            "intent": final_state.get("intent", existing.get("intent", "UNKNOWN") if existing else "UNKNOWN"),
            "final_report": final_state.get("final_report", ""),
            "sources": final_state.get("all_sources", []),
            "citations": final_state.get("citations", []),
            "execution_time": execution_time,
            "created_at": existing.get("created_at", datetime.now(timezone.utc)) if existing else datetime.now(timezone.utc),
        }
    )

    return ResearchResponse(
        thread_id=thread_id,
        status="completed" if final_state.get("approved") else "awaiting_review",
        report=final_state.get("final_report", ""),
        citations=final_state.get("citations", []),
        sources=final_state.get("all_sources", []),
        execution_time=execution_time,
    )


@router.get("/admin/stats", response_model=SystemStats)
def get_system_stats():
    """System statistics for the current backend process."""
    return SystemStats(**runtime_store.stats())


@router.get("/admin/history")
def get_query_history(limit: int = 20):
    """Recent research queries from the in-memory store."""
    queries = runtime_store.list_history(limit=limit)
    return [
        {
            "id": index + 1,
            "thread_id": item["thread_id"],
            "query": item["query"][:100] + "..." if len(item["query"]) > 100 else item["query"],
            "status": item["status"],
            "intent": item.get("intent"),
            "execution_time": item.get("execution_time"),
            "created_at": item.get("created_at").isoformat() if item.get("created_at") else None,
        }
        for index, item in enumerate(queries)
    ]


@router.get("/health", response_model=HealthCheck)
def health_check():
    """Health check endpoint."""
    return HealthCheck(
        status="healthy",
        version=settings.VERSION,
        uptime=time.time(),
        database="disabled",
        llm_service="configured" if settings.OPENAI_API_KEY else "missing_api_key",
        timestamp=datetime.now(timezone.utc),
    )