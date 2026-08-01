from collections import Counter

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.models import OrchestratorRequest, OrchestratorResponse
from backend import orchestrator
from backend.services import rag

app = FastAPI(title="Multi-Agent Research Platform (MVP)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for a 4-day demo; lock down later
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/query", response_model=OrchestratorResponse)
async def query(req: OrchestratorRequest):
    """Single entry point — orchestrator decides which agent handles it."""
    return await orchestrator.route(req.query,req.num_papers)


@app.get("/dashboard/activity")
async def dashboard_activity():
    """Basic activity analytics, pulled from what's actually been stored via RAG.

    Real (not mocked) as long as at least one /query call has been made;
    the topic-distribution chart on the dashboard reads from this.
    """
    logs = rag.query_activity_log()
    topics = Counter(entry["topic"] for entry in logs)
    return {
        "total_papers_indexed": len(logs),
        "queries_by_topic": topics.most_common(10),
    }
