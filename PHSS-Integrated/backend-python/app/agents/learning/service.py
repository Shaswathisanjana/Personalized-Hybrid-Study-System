"""Cognitive Learning Agent service with persistent cognitive memory and zero content fabrication."""
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Add vendor directory to sys.path so cognitive_learning_agent can be imported cleanly
VENDOR_DIR = Path(__file__).resolve().parent.parent.parent.parent / "vendor"
if str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))

from cognitive_learning_agent.core.agent import LearningAgent
from cognitive_learning_agent.models.schemas import (
    LearnerProfileCreate,
    DifficultyLevel,
    LearningFormat,
    LearningPath,
    QuizSubmission,
    AssessmentFeedback,
)
from app.database.mongo import get_db

logger = logging.getLogger(__name__)

# Global singleton LearningAgent instance
_agent: Optional[LearningAgent] = None

def get_learning_agent() -> LearningAgent:
    global _agent
    if _agent is None:
        _agent = LearningAgent()
    return _agent


def _map_difficulty(level_str: str) -> DifficultyLevel:
    clean = (level_str or "").strip().lower()
    if "adv" in clean:
        return DifficultyLevel.ADVANCED
    if "inter" in clean or "med" in clean:
        return DifficultyLevel.INTERMEDIATE
    return DifficultyLevel.BEGINNER


def _format_plan_dict(user_id: str, topic: str, difficulty: DifficultyLevel, goal_text: str, learning_path: LearningPath) -> dict[str, Any]:
    from app.agents.learning.modules import build_modules
    steps = build_modules(learning_path.ordered_concepts, learning_path.resources, difficulty.value)

    now = datetime.now(timezone.utc)
    return {
        "userId": user_id,
        "topic": topic,
        "currentLevel": difficulty.value,
        "goal": goal_text,
        "rationale": learning_path.rationale or f"Curated cognitive learning journey for {topic}",
        "steps": steps,
        "resources": [r.model_dump() for r in learning_path.resources],
        "orderedConcepts": learning_path.ordered_concepts,
        "estimatedTotalMinutes": learning_path.estimated_total_minutes,
        "createdAt": now,
        "updatedAt": now,
        "status": "active",
        "source": "cognitive-learning-agent",
    }


def attach_course_progress(user_id: str, plan: dict) -> dict:
    from app.agents.learning.course_progress import annotate_plan
    try:
        records=list(get_db().quiz_attempts.find({"userId":user_id,"courseTopic":plan.get("topic","")}).sort("createdAt",-1))
    except Exception:
        return plan
    return annotate_plan(plan,records)


def create_learning_plan(
    user_id: str,
    topic: str,
    current_level: str = "beginner",
    goal: str = "Understand the topic",
    force_new: bool = False
) -> dict[str, Any]:
    from app.orchestrator.intents import normalize_learning_topic
    topic = normalize_learning_topic((topic or "").strip())
    if not topic:
        raise ValueError("Topic must contain between 1 and 250 characters.")
    if len(topic) > 250:
        topic = topic[:250].strip()

    goal_text = (goal or f"Master {topic}").strip()
    if len(goal_text) > 500:
        goal_text = goal_text[:500].strip()

    difficulty = _map_difficulty(current_level)
    agent = get_learning_agent()

    # Step 1: Check if an existing journey matches this topic
    existing_match = None
    if not force_new:
        try:
            existing_match = agent.find_similar_learning_journey(topic, user_id)
        except Exception as e:
            logger.debug(f"Error checking similar journey: {e}")

    if existing_match:
        matched = str(existing_match.get("topic_title") or "").strip().casefold()
        if matched != topic.casefold():
            existing_match = None
    if existing_match and not force_new:
        learning_path = None
        if existing_match.get("path_json"):
            try:
                p_dict = json.loads(existing_match["path_json"])
                learning_path = LearningPath(**p_dict)
            except Exception:
                learning_path = None
        if not learning_path:
            try:
                learning_path = agent.get_current_learning_path(existing_match.get("learner_id") or user_id)
            except Exception:
                learning_path = None

        if learning_path and learning_path.resources:
            matched_title = existing_match.get("topic_title") or topic
            existing_plan = _format_plan_dict(
                user_id=user_id,
                topic=matched_title,
                difficulty=difficulty,
                goal_text=existing_match.get("learning_goal") or goal_text,
                learning_path=learning_path
            )
            # Keep the preview available for a later explicit enrollment.
            get_db().learning_plans.update_one(
                {"userId": user_id, "topic": matched_title},
                {"$set": existing_plan}, upsert=True
            )
            existing_plan = attach_course_progress(user_id,existing_plan)
            prog_val = round(float(existing_match.get("progress_percentage", existing_match.get("mastery_percentage", 0.0))))
            return {
                "existing_found": True,
                "existing_topic": matched_title,
                "existing_goal": existing_match.get("learning_goal") or existing_match.get("target_outcome") or goal_text,
                "existing_mastery": prog_val,
                "existing_completed": existing_match.get("completed_topics", 0),
                "existing_total": existing_match.get("total_topics", len(learning_path.resources)),
                "existing_journey_id": existing_match.get("id"),
                "existing_plan": existing_plan,
                "topic": topic,
                "message": f"An existing roadmap for '{matched_title}' already exists ({prog_val}% Mastery)."
            }

    # Generate fresh path
    profile_input = LearnerProfileCreate(
        user_id=user_id,
        name=user_id,
        learning_goal=topic,
        current_level=difficulty,
        preferred_format=LearningFormat.ANY,
        target_outcome=goal_text,
        preferred_language="Python",
    )
    _, learning_path = agent.start_learning_journey(profile_input)
    plan = _format_plan_dict(user_id, topic, difficulty, goal_text, learning_path)

    # Persist in MongoDB
    try:
        db = get_db()
        db.learning_plans.update_one(
            {"userId": user_id, "topic": topic},
            {"$set": plan},
            upsert=True
        )

        now = datetime.now(timezone.utc)
        cog_state = agent.get_cognitive_state(user_id)
        state_doc = {
            "userId": user_id,
            "topic": topic,
            "overallProgress": cog_state.overall_progress if cog_state else 0.0,
            "concepts": {k: v.model_dump() for k, v in cog_state.concepts.items()} if cog_state else {},
            "activeMisconceptions": [m.model_dump() for m in cog_state.active_misconceptions] if cog_state else [],
            "rectifiedMisconceptions": [m.model_dump() for m in cog_state.rectified_misconceptions] if cog_state else [],
            "updatedAt": now,
        }
        db.learning_states.update_one(
            {"userId": user_id, "topic": topic},
            {"$set": state_doc},
            upsert=True
        )
    except Exception as db_err:
        logger.warning(f"Failed to persist plan to MongoDB: {db_err}")

    plan.pop("_id", None)
    return attach_course_progress(user_id,plan)


def get_learning_state(user_id: str, topic: str) -> dict[str, Any] | None:
    try:
        agent = get_learning_agent()
        cog = agent.get_cognitive_state(user_id)
        if cog and cog.concepts:
            return {
                "userId": user_id,
                "topic": topic,
                "overallProgress": cog.overall_progress,
                "concepts": {k: v.model_dump() for k, v in cog.concepts.items()},
                "activeMisconceptions": [m.model_dump() for m in cog.active_misconceptions],
                "rectifiedMisconceptions": [m.model_dump() for m in cog.rectified_misconceptions],
            }
    except Exception as e:
        logger.debug(f"Error fetching state from cognitive agent: {e}")

    try:
        row = get_db().learning_states.find_one({"userId": user_id, "topic": topic}, {"_id": 0})
        return row
    except Exception:
        return None


def generate_concept_quiz(
    user_id: str,
    concept_name: str,
    resource_url: str = "",
    force_refresh: bool = False,
    attempt_number: Optional[int] = None,
    current_level: str = "",
) -> dict[str, Any]:
    from app.agents.learning.video_context import video_context
    source_context, basis = video_context(resource_url)
    if current_level in {"beginner","intermediate","advanced"}:
        source_context = f"Requested assessment difficulty: {current_level}.\n" + (source_context or "")
    agent = get_learning_agent()
    quiz = agent.generate_quiz_for_resource(
        user_id=user_id,
        concept_name=concept_name,
        resource_url=resource_url,
        force_refresh=force_refresh,
        attempt_number=attempt_number,
        resource_context=source_context,
    )
    res = quiz.model_dump()
    res["assessment_basis"] = basis
    res["source_note"] = "Video captions were retrieved and supplied to the quiz generator." if basis == "video_transcript" else "Captions unavailable: this quiz assesses the topic, not verified video-specific content." if basis == "concept_no_transcript" else "Concept diagnostic assessment."
    # Attach past attempts summary so UI can display history context
    past_attempts = agent.repository.get_quiz_attempts(user_id, concept_name)
    res["past_attempts_count"] = len(past_attempts)
    res["past_attempts"] = [att.model_dump() for att in past_attempts]
    return res


def submit_concept_quiz(
    user_id: str,
    concept_name: str,
    resource_url: str,
    answers: dict[str, int] = None,
    descriptive_answers: dict[str, str] = None,
    attempt_number: Optional[int] = None,
    course_topic: str = "",
    lesson_key: str = "",
) -> dict[str, Any]:
    agent = get_learning_agent()
    int_answers = {int(k): int(v) for k, v in (answers or {}).items()}
    int_desc = {int(k): str(v) for k, v in (descriptive_answers or {}).items()}
    sub = QuizSubmission(
        learner_id=user_id,
        concept_name=concept_name,
        resource_url=resource_url,
        attempt_number=attempt_number,
        selected_answers=int_answers,
        descriptive_answers=int_desc,
    )
    result = agent.evaluate_quiz_and_remedy(sub)
    res_dict = result.model_dump()

    # Persist the graded attempt independently of optional cognitive snapshots.
    now = datetime.now(timezone.utc)
    try:
        get_db().quiz_attempts.insert_one({
            "userId": user_id,
            "conceptName": concept_name,
            "courseTopic": course_topic[:250],
            "lessonKey": lesson_key[:160],
            "attemptNumber": result.attempt_number,
            "quizType": result.quiz_type,
            "score": result.score,
            "passed": result.passed,
            "totalQuestions": result.total_questions,
            "correctCount": result.correct_count,
            "nextAction": result.next_action.value if hasattr(result.next_action, "value") else str(result.next_action),
            "nextActionReason": result.next_action_reason,
            "weakAreas": result.weak_areas,
            "misconceptions": result.detected_misconceptions,
            "remediationEfficacy": result.remediation_efficacy,
            "createdAt": now,
        })
        res_dict["progressSaved"] = True
    except Exception:
        logger.warning("Quiz was graded but course-progress persistence failed.")
        res_dict["progressSaved"] = False
        res_dict["progressWarning"] = "Your quiz was graded, but saving course progress failed. Keep this result open and check the database connection."
    try:
        cog = agent.get_cognitive_state(user_id)
        if cog is not None:
            get_db().learning_states.update_one(
                {"userId":user_id},
                {"$set":{"overallProgress":cog.overall_progress,
                         "concepts":{k:v.model_dump() for k,v in cog.concepts.items()},
                         "activeMisconceptions":[m.model_dump() for m in cog.active_misconceptions],
                         "updatedAt":now}},upsert=True)
    except Exception:
        logger.warning("Cognitive snapshot refresh failed; graded quiz result was handled separately.")

    return res_dict


def get_quiz_history(user_id: str, concept_name: Optional[str] = None) -> list[dict[str, Any]]:
    agent = get_learning_agent()
    attempts = agent.repository.get_quiz_attempts(user_id, concept_name)
    return [att.model_dump() for att in attempts]


def get_learning_journeys(user_id: Optional[str] = None) -> list[dict[str, Any]]:
    if not user_id:
        raise ValueError("A signed-in learner is required to load courses.")
    # Only user-confirmed enrollments belong on the dashboard.
    journeys = []
    enrolled_topics = [d["topic"] for d in get_db().course_enrollments.find({"userId": user_id})]
    mongo_plans = []
    try:
        query = {"userId": user_id, "topic": {"$in": enrolled_topics}}
        for doc in get_db().learning_plans.find(query).sort("updatedAt", -1):
            mongo_plans.append({
                "id": str(doc.get("_id")),
                "topic_title": doc.get("topic", "Untitled Topic"),
                "learning_goal": doc.get("goal", ""),
                "target_outcome": doc.get("goal", ""),
                "total_topics": len(doc.get("steps", [])),
                "completed_topics": 0,
                "progress_percentage": 0.0,
                "updated_at": doc.get("updatedAt", doc.get("createdAt")),
                "learner_id": doc.get("userId"),
                "plan": {
                    "topic": doc.get("topic"),
                    "rationale": doc.get("rationale"),
                    "steps": doc.get("steps"),
                    "currentLevel": doc.get("currentLevel"),
                    "resources":doc.get("resources",[]),
                    "orderedConcepts":doc.get("orderedConcepts",[]),
                }
            })
    except Exception as e:
        logger.debug(f"Error fetching mongo plans: {e}")


    all_raw = journeys + mongo_plans
    deduped: list[dict[str, Any]] = []

    for item in all_raw:
        title = (item.get("topic_title") or "").strip()
        if not title:
            continue

        matched_idx = -1
        for idx, existing in enumerate(deduped):
            ex_title = existing.get("topic_title") or ""
            normalized = lambda value: ' '.join(value.casefold().replace('_',' ').split())
            if normalized(title) == normalized(ex_title):
                matched_idx = idx
                break

        prog = float(item.get("progress_percentage", item.get("mastery_percentage", 0.0)))
        item_copy = dict(item)
        if hasattr(item_copy.get("updated_at"), "isoformat"):
            item_copy["updated_at"] = item_copy["updated_at"].isoformat()
        if hasattr(item_copy.get("created_at"), "isoformat"):
            item_copy["created_at"] = item_copy["created_at"].isoformat()

        if matched_idx >= 0:
            existing = deduped[matched_idx]
            ex_prog = float(existing.get("progress_percentage", existing.get("mastery_percentage", 0.0)))
            if prog > ex_prog:
                deduped[matched_idx] = item_copy
            elif not existing.get("plan") and item_copy.get("plan"):
                existing["plan"] = item_copy["plan"]
        else:
            deduped.append(item_copy)

    from app.agents.learning.course_progress import annotate_plan
    try:
        attempts=list(get_db().quiz_attempts.find({"userId":user_id}).sort("createdAt",-1))
    except Exception:
        attempts=[]
    for item in deduped:
        if not item.get('plan') and item.get('path_json'):
            try:
                item['plan']=_format_plan_dict(user_id,item['topic_title'],DifficultyLevel.BEGINNER,item.get('learning_goal',''),LearningPath(**json.loads(item['path_json'])))
            except Exception:
                pass
        plan=item.get('plan')
        if plan and plan.get('orderedConcepts'):
            from app.agents.learning.modules import build_modules
            plan['steps']=build_modules(plan['orderedConcepts'],plan.get('resources') or plan.get('steps',[]),plan.get('currentLevel') or 'beginner')
        if plan:
            item['plan']=annotate_plan(plan,attempts)
            progress=item['plan']['quizProgress']
            item['completed_lessons']=progress['completed']
            item['total_lessons']=progress['total']
            item['course_completion_percentage']=progress['percentage']
    return deduped


def enroll_course(user_id: str, topic: str) -> dict:
    db = get_db()
    topic = topic.strip()
    if not user_id:
        raise ValueError("Sign in before enrolling.")
    plan = db.learning_plans.find_one({"userId": user_id, "topic": topic})
    if not plan or not plan.get("steps"):
        raise ValueError("Create a learning roadmap before enrolling.")
    import hashlib
    identity = hashlib.sha256(repr((user_id, topic)).encode()).hexdigest()
    db.course_enrollments.update_one({"_id": identity}, {"$setOnInsert": {
        "userId": user_id, "topic": topic, "enrolledAt": datetime.now(timezone.utc)
    }}, upsert=True)
    return {"ok": True, "enrolled": True, "topic": topic}
