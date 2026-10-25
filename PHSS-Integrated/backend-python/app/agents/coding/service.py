"""Stores coding feedback events; code execution remains in the isolated existing coding service."""
from datetime import datetime, timezone
from app.database.mongo import get_db

def record_feedback(user_id: str, topic: str, status: str, feedback: str, attempt_id: str = "") -> dict:
    if not topic.strip():
        raise ValueError("A topic or problem title is required.")
    allowed = {"passed", "failed", "partial", "unknown"}
    result_status = status if status in allowed else "unknown"
    now = datetime.now(timezone.utc)
    doc = {"userId": user_id, "topic": topic[:250], "status": result_status, "feedback": feedback[:4000], "attemptId": attempt_id[:100], "createdAt": now, "evidenceType": "user_or_coding_service_report"}
    get_db().coding_feedback.insert_one(doc)
    # This endpoint accepts user-visible feedback, not a trusted judge verdict.
    # It deliberately does not change mastery; only a verified server-side result
    # from the Coding Agent may update the cognitive state.
    return {"saved": True, "status": result_status, "message": "Feedback saved as provisional evidence. Mastery is not changed by an unverified client-reported result."}
