"""Capture plain data and reconnect runtime services to restored shared CACM."""
from __future__ import annotations

from dataclasses import fields, is_dataclass

from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.models import StudentCognitiveModel
from app.learning_agent.progress_tracker import LearningProgressTracker
from app.persistence.state_codec import encode, decode
from app.persistence.concept_migration import migrate_concepts
from app.cognitive.concept_identity import IDENTITY_VERSION


UI_KEYS = frozenset((
    "standalone_code_review", "practice_topic_sessions",
    "journey_clarification",
    "journey_workspace",
    "journey_topic", "journey_navigation", "_app_page",
    "advanced_research_topic_input", "advanced_research_concept_input",
    "advanced_research_job",
    "learning_goal", "learning_diagnostic_concept", "learning_diagnostic_session",
    "learning_diagnostic_outcome",
    "last_result", "last_query", "practice_session", "practice_feedback",
    "practice_summary", "practice_concept", "practice_context", "practice_last_outcome",
    "waiting_for_next_question", "last_answered_question", "last_student_answer",
    "selected_practice_question_count", "learning_request_input",
    "advanced_coding_exercise", "advanced_coding_loaded_concept", "advanced_coding_concept",
    "advanced_coding_editor", "advanced_coding_hint_history",
    "advanced_coding_free_topic", "advanced_coding_language", "advanced_coding_generation_attempts",
    "advanced_coding_generation_status", "advanced_coding_guided_result", "advanced_coding_guided_source",
    "advanced_coding_practice_focus", "advanced_coding_topic_drafts", "advanced_coding_execution_preview", "advanced_coding_review_error",
    "advanced_coding_submission_record", "advanced_coding_submission_source",
    "advanced_coding_diagnostic_session", "advanced_coding_diagnostic_result",
    "advanced_coding_diagnostic_concept", "advanced_coding_review_outcome",
    "advanced_coding_review_source", "advanced_coding_target_concept",
    "advanced_research_result", "advanced_research_action", "advanced_research_plan",
    "advanced_research_concept", "research_assessment_question",
    "research_assessment_completed", "research_assessment_feedback",
    "research_diagnostic_session", "research_diagnostic_concept", "research_diagnostic_outcome",
    "_assessment_pending",
))
SERVICE_KEYS = frozenset((
    "learning_diagnostic_bridge",
    "advanced_coding_controller", "advanced_coding_hint_engine",
    "advanced_coding_diagnostic_bridge", "research_assessment_service",
    "research_diagnostic_bridge", "research_diagnostic_engine",
    "research_diagnostic_student_id",
))


def capture(state):
    student = state["student"]
    engine = state["orchestrator"].cognitive_engine
    tracker = state["learning_progress_tracker"]
    guards = {}
    controller = state.get("advanced_coding_controller")
    if controller is not None:
        guards["coding_records"] = controller.records
    service = state.get("research_assessment_service")
    if service is not None:
        guards["research_submitted"] = service._submitted_question_ids
    hints = state.get("advanced_coding_hint_engine")
    if hints is not None:
        guards["hint_counts"] = hints.hint_engine._request_counts
    for key in ("advanced_coding_diagnostic_bridge", "research_diagnostic_bridge", "learning_diagnostic_bridge"):
        bridge = state.get(key)
        if bridge is not None:
            guards[key] = bridge.runtime.diagnostic_intervention.completed_sessions
    data = {
        "student": student,
        "evidence": engine.evidence_store.get_all_evidence(),
        "conflicts": engine.active_conflicts,
        "progress": tracker._records,
        "completions": tracker._recorded_completions,
        "ui": {k: state[k] for k in UI_KEYS if k in state},
        "guards": guards,
        "identity_archive": state.get("_concept_identity_archive", {}),
        "assessment_records": getattr(engine, "assessment_records", {}),
        "evidence_receipts": getattr(engine, "evidence_receipts", {}),
    }
    # Reconstitute old dataclass instances through the same safe migration path
    # used on disk. This also handles sessions retained during a code reload.
    data = decode(encode(data))
    validate(data, student.user_id)
    # Migration must not mutate objects currently rendered by Streamlit.
    data = migrate_concepts(data)
    validate(data, student.user_id)
    return {"version": 1, "student_id": student.user_id,
            "concept_identity_version": IDENTITY_VERSION,
            "assessment_transaction_version": 1, "data": encode(data)}


def validate(data, student_id):
    """Reject cross-student or structurally invalid state before touching live state."""
    required = {"student", "evidence", "conflicts", "progress", "completions", "ui", "guards"}
    if not required <= set(data) or set(data) - required - {"identity_archive", "assessment_records", "evidence_receipts"}:
        raise ValueError("Incomplete student snapshot.")
    if not isinstance(data.get("identity_archive", {}), dict):
        raise ValueError("Invalid identity migration archive.")
    for name in ("assessment_records", "evidence_receipts"):
        records = data.get(name, {})
        if not isinstance(records, dict) or any(not isinstance(key, tuple) or len(key) != 2
                or key[0] != student_id or not isinstance(key[1], str) for key in records):
            raise ValueError("Invalid or cross-student assessment records.")
    if not isinstance(data["student"], StudentCognitiveModel):
        raise ValueError("Invalid student model.")
    if data["student"].user_id != student_id or not isinstance(data["ui"], dict):
        raise ValueError("Snapshot belongs to another student.")
    if set(data["ui"]) - UI_KEYS:
        raise ValueError("Unknown saved UI state.")
    pending = data["ui"].get("journey_clarification")
    if pending is not None and (not isinstance(pending, dict) or pending.get("user_id") != student_id
            or any(not isinstance(pending.get(k), str) or len(pending[k]) > 8000 for k in ("query", "question", "topic"))):
        raise ValueError("Invalid or cross-student clarification.")
    review=data["ui"].get("standalone_code_review")
    if review is not None and (not isinstance(review,dict) or review.get("user_id")!=student_id
            or not isinstance(review.get("code"),str) or len(review["code"])>100000
            or not isinstance(review.get("context"),str) or len(review["context"])>8000
            or review.get("status") not in {"draft","running","ready","error"}):
        raise ValueError("Invalid or cross-student standalone review.")
    cache=data['ui'].get('practice_topic_sessions',{})
    from app.learning_agent.practice_session import PracticeSession
    from app.cognitive.concept_identity import concept_id
    if not isinstance(cache,dict):raise ValueError('Invalid topic practice cache.')
    for topic,entry in cache.items():
        if (not isinstance(topic,str) or not isinstance(entry,dict) or set(entry)-{'session','feedback'}
                or not isinstance(entry.get('session'),PracticeSession)
                or concept_id(entry['session'].concept_name)!=topic):
            raise ValueError('Invalid topic practice cache entry.')
    from app.orchestrator.study_workspace import validate_workspace
    validate_workspace({"student": data["student"], "journey_workspace": data["ui"].get("journey_workspace")})
    from app.cognitive.models import ConceptState
    from app.cognitive.evidence import LearningEvidence
    from app.cognitive.conflict_detector import CognitiveConflict
    from app.learning_agent.progress_tracker import TopicLearningProgress
    if not isinstance(data["student"].concepts, dict):
        raise ValueError("Invalid concept map.")
    for name, concept in data["student"].concepts.items():
        if not isinstance(concept, ConceptState) or name != concept.concept_name:
            raise ValueError("Invalid concept state.")
        if any(type(v) not in (float, int) or not 0 <= v <= 1 for v in (concept.mastery, concept.confidence)):
            raise ValueError("Invalid cognitive estimate.")
        if type(concept.attempts) is not int or concept.attempts < 0:
            raise ValueError("Invalid cognitive attempt count.")
    if not isinstance(data["evidence"], list) or any(not isinstance(e, LearningEvidence) for e in data["evidence"]):
        raise ValueError("Invalid evidence history.")
    for name in ("conflicts", "progress"):
        if not isinstance(data[name], dict):
            raise ValueError("Invalid saved " + name)
        for key in data[name]:
            if not isinstance(key, tuple) or len(key) != 2 or key[0] != student_id:
                raise ValueError("Cross-student snapshot key.")
    if any(not isinstance(v, list) or any(not isinstance(c, CognitiveConflict) for c in v)
           for v in data["conflicts"].values()):
        raise ValueError("Invalid conflict records.")
    if any(not isinstance(v, TopicLearningProgress) for v in data["progress"].values()):
        raise ValueError("Invalid progress records.")
    if not isinstance(data["completions"], set):
        raise ValueError("Invalid completion guards.")
    if any(not isinstance(k, tuple) or len(k) != 3 or k[0] != student_id for k in data["completions"]):
        raise ValueError("Cross-student completion identifier.")
    if not isinstance(data["guards"], dict) or set(data["guards"]) - {
        "coding_records", "research_submitted", "hint_counts",
        "advanced_coding_diagnostic_bridge", "research_diagnostic_bridge",
        "learning_diagnostic_bridge",
    }:
        raise ValueError("Invalid assessment guards.")

    def check_owner(value):
        if is_dataclass(value) and not isinstance(value, type):
            if hasattr(value, "user_id") and value.user_id != student_id:
                raise ValueError("Cross-student assessment or evidence.")
            for f in fields(value):
                check_owner(getattr(value, f.name))
        elif isinstance(value, dict):
            for v in value.values():
                check_owner(v)
        elif isinstance(value, (list, tuple, set)):
            for v in value:
                check_owner(v)
    check_owner(data)


def unpack(payload, student_id):
    if payload.get("version") != 1 or payload.get("student_id") != student_id:
        raise ValueError("Unsupported snapshot version or student identity.")
    if payload.get("concept_identity_version") not in (None, IDENTITY_VERSION):
        raise ValueError("Unsupported concept identity version.")
    if payload.get("assessment_transaction_version") not in (None, 1):
        raise ValueError("Unsupported assessment transaction version.")
    data = decode(payload["data"])
    validate(data, student_id)
    migrate_concepts(data)
    validate(data, student_id)
    return data


def restore(payload, student_id, orchestrator_factory):
    # Decode everything first: malformed snapshots never produce a half-loaded UI.
    data = unpack(payload, student_id)
    engine = CognitiveEngine()
    engine.evidence_store.evidence_history = data["evidence"]
    engine.active_conflicts = data["conflicts"]
    engine.assessment_records = data.get("assessment_records", {})
    engine.evidence_receipts = data.get("evidence_receipts", {})
    tracker = LearningProgressTracker()
    tracker._records = data["progress"]
    tracker._recorded_completions = data["completions"]
    state = dict(data["ui"])
    state.update(student=data["student"], orchestrator=orchestrator_factory(engine),
                 learning_progress_tracker=tracker,
                 _concept_identity_archive=data.get("identity_archive", {}))
    rebuild_services(state, data["guards"])
    return state


def rebuild_services(state, guards):
    student = state["student"]
    engine = state["orchestrator"].cognitive_engine
    exercise = state.get("advanced_coding_exercise")
    if exercise is not None:
        from app.coding_agent.integrated_workflow import IntegratedCodingWorkflow
        from app.coding_agent.submission_controller import CodingSubmissionController
        from app.coding_agent.adaptive_hint_coordinator import MisconceptionAwareHintCoordinator
        controller = CodingSubmissionController(IntegratedCodingWorkflow(student, engine), exercise)
        controller.records = guards.get("coding_records", {})
        state["advanced_coding_controller"] = controller
        hints = MisconceptionAwareHintCoordinator()
        hints.hint_engine._request_counts = guards.get("hint_counts", {})
        state["advanced_coding_hint_engine"] = hints
    if state.get("advanced_research_result") is not None:
        from app.research_agent.personalized_coordinator import PersonalizedResearchCoordinator
        from app.research_agent.assessment_service import ResearchAssessmentService
        service = ResearchAssessmentService(PersonalizedResearchCoordinator(student, engine))
        service._submitted_question_ids = guards.get("research_submitted", set())
        state["research_assessment_service"] = service
    for prefix, module, name in (
        ("learning", "app.learning_agent.diagnostic_bridge", "LearningDiagnosticBridge"),
        ("advanced_coding", "app.coding_agent.diagnostic_bridge", "CodingDiagnosticBridge"),
        ("research", "app.research_agent.diagnostic_bridge", "ResearchDiagnosticBridge"),
    ):
        key = prefix + "_diagnostic_bridge"
        if key in guards or state.get(prefix + "_diagnostic_session") is not None:
            from importlib import import_module
            bridge_class = getattr(import_module(module), name)
            bridge = (bridge_class(student, engine, getattr(state["orchestrator"], "learning_runtime", None))
                      if prefix == "learning" else bridge_class(student, engine))
            bridge.runtime.diagnostic_intervention.completed_sessions = guards.get(key, {})
            state[key] = bridge
            if prefix == "research":
                state["research_diagnostic_student_id"] = student.user_id
                state["research_diagnostic_engine"] = engine
