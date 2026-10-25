"""PHSS AI service. Node.js is the only public application API; this service is internal."""
from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel, Field
from app.core.config import settings
from app.database.mongo import get_db, ping_database
from app.agents.learning.service import (
    create_learning_plan,
    get_learning_state,
    generate_concept_quiz,
    submit_concept_quiz,
    get_quiz_history,
)
from app.agents.research.service import search_papers
from app.agents.coding.service import record_feedback
from app.orchestrator.graph import run_orchestrator

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        ping_database()
        print("[phss-ai] Connected to MongoDB.")
    except Exception as exc:
        print(f"[phss-ai] MongoDB ping warning at startup: {exc}. Server will start and reconnect when database is ready.")
    yield

app = FastAPI(title="PHSS AI Service", version="1.0.0", lifespan=lifespan)

class BaseRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=100)
    user_name: str = Field(default="", max_length=100)

class LearningRequest(BaseRequest):
    topic: str = Field(min_length=1, max_length=250)
    current_level: str = Field(default="beginner", max_length=30)
    goal: str = Field(default="understand the topic", max_length=500)
    force_new: bool = Field(default=False)

class ResearchRequest(BaseRequest):
    topic: str = Field(min_length=1, max_length=300)
    count: int = Field(default=5, ge=1, le=10)
    full_analysis: bool = Field(default=True)

class CodingRequest(BaseRequest):
    topic: str = Field(min_length=1, max_length=250)
    status: str = Field(default="unknown", max_length=30)
    feedback: str = Field(default="", max_length=4000)
    attempt_id: str = Field(default="", max_length=100)

class OrchestratorRequest(BaseRequest):
    message: str = Field(min_length=1, max_length=2000)
    mode: str = Field(default="auto", max_length=30)
    context: dict[str, Any] = Field(default_factory=dict)

def require_service_key(x_phss_service_key: str | None = Header(default=None)):
    expected = settings.service_key
    if not expected or not x_phss_service_key or x_phss_service_key != expected:
        raise HTTPException(status_code=403, detail="Internal service authentication failed.")

@app.get("/health")
def health() -> dict[str, Any]:
    try:
        ping_database()
        return {"ok": True, "service": "phss-ai", "database": "connected"}
    except Exception:
        return {"ok": False, "service": "phss-ai", "database": "unavailable"}

class QuizRequest(BaseRequest):
    current_level: str = Field(default="", max_length=30)
    concept_name: str = Field(min_length=1, max_length=250)
    resource_url: str = Field(default="", max_length=1000)
    force_refresh: bool = Field(default=False)
    attempt_number: int | None = Field(default=None)

class QuizSubmitRequest(BaseRequest):
    course_topic: str = Field(default="", max_length=250)
    lesson_key: str = Field(default="", max_length=160)
    concept_name: str = Field(min_length=1, max_length=250)
    resource_url: str = Field(default="", max_length=1000)
    attempt_number: int | None = Field(default=None)
    answers: dict[str, int] = Field(default_factory=dict)
    descriptive_answers: dict[str, str] = Field(default_factory=dict)

@app.post("/internal/agents/learning/plan", dependencies=[Depends(require_service_key)])
def learning_plan(body: LearningRequest) -> dict:
    try:
        plan = create_learning_plan(body.user_id, body.topic, body.current_level, body.goal, body.force_new)
        if plan.get("existing_found"):
            return {"ok": True, "existing_found": True, "existing_roadmap": plan}
        state = get_learning_state(body.user_id, body.topic)
        return {"ok": True, "plan": plan, "cognitiveState": state}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/internal/agents/learning/quiz", dependencies=[Depends(require_service_key)])
def learning_quiz(body: QuizRequest) -> dict:
    try:
        quiz = generate_concept_quiz(
            user_id=body.user_id,
            current_level=body.current_level,
            concept_name=body.concept_name,
            resource_url=body.resource_url,
            force_refresh=body.force_refresh,
            attempt_number=body.attempt_number,
        )
        return {"ok": True, "quiz": quiz}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/internal/agents/learning/quiz/submit", dependencies=[Depends(require_service_key)])
def learning_quiz_submit(body: QuizSubmitRequest) -> dict:
    try:
        eval_res = submit_concept_quiz(
            user_id=body.user_id,
            concept_name=body.concept_name,
            resource_url=body.resource_url,
            answers=body.answers,
            descriptive_answers=body.descriptive_answers,
            attempt_number=body.attempt_number,
            course_topic=body.course_topic,
            lesson_key=body.lesson_key,
        )
        return {"ok": True, "evaluation": eval_res}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.get("/internal/agents/learning/quiz/history", dependencies=[Depends(require_service_key)])
def learning_quiz_history(user_id: str = "", concept_name: str = "") -> dict:
    try:
        history = get_quiz_history(user_id, concept_name or None)
        return {"ok": True, "history": history}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/internal/agents/learning/enroll", dependencies=[Depends(require_service_key)])
def learning_enroll(body: LearningRequest) -> dict:
    from app.agents.learning.service import enroll_course
    try:
        return enroll_course(body.user_id, body.topic)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.get("/internal/agents/learning/journeys", dependencies=[Depends(require_service_key)])
def learning_journeys(user_id: str = "") -> dict:
    try:
        from app.agents.learning.service import get_learning_journeys
        journeys = get_learning_journeys(user_id or None)
        return {"ok": True, "journeys": journeys}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/internal/agents/research/search", dependencies=[Depends(require_service_key)])
def research_search(body: ResearchRequest) -> dict:
    try:
        return {"ok": True, "research": search_papers(body.user_id, body.topic, body.count, full_analysis=body.full_analysis)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

@app.post("/internal/agents/research/export-docx", dependencies=[Depends(require_service_key)])
def research_export_docx(body: dict[str, Any]):
    try:
        from fastapi.responses import Response
        from app.agents.research.word_export import export_word_report
        docx_bytes = export_word_report(body)
        filename = f"research_literature_report_{int(__import__('time').time())}.docx"
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

@app.post("/internal/agents/coding/feedback", dependencies=[Depends(require_service_key)])
def coding_feedback(body: CodingRequest) -> dict:
    try:
        return {"ok": True, "feedback": record_feedback(body.user_id, body.topic, body.status, body.feedback, body.attempt_id)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@app.post("/internal/orchestrator/chat", dependencies=[Depends(require_service_key)])
def orchestrate(body: OrchestratorRequest) -> dict:
    try:
        result = run_orchestrator(body.user_id, body.message, body.mode, body.context)
        try:
            get_db().agent_sessions.insert_one({"userId": body.user_id, "message": body.message, "mode": body.mode, "result": result, "createdAt": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)})
        except Exception as db_err:
            print(f"[phss-ai] Warning: could not log session to DB: {db_err}")
        return {"ok": True, "result": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=502, detail=f"The selected agent could not complete this request: {str(exc)}") from exc

@app.post("/internal/cacm/snapshot", dependencies=[Depends(require_service_key)])
def cacm_snapshot(body: BaseRequest):
    from app.agents.cacm import snapshot
    return {"ok": True, "cognitive": snapshot(body.user_id)}

@app.post("/internal/agents/learning/video", dependencies=[Depends(require_service_key)])
def create_video(body: LearningRequest):
    from app.agents.video import lesson_video
    try:
        return {"ok": True, "video": lesson_video(body.topic)}
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
