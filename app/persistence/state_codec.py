"""JSON codec restricted to existing PHSS data classes, never executable objects."""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import datetime
from functools import lru_cache
from importlib import import_module
import math
import hashlib
import json

# Explicit module allowlist: payloads cannot select arbitrary imports/classes.
DATA_MODULES = (
    "cognitive.models", "cognitive.evidence", "cognitive.misconception_tracker",
    "cognitive.conflict_detector", "cognitive.conflict_resolver",
    "cognitive.diagnostic_intervention", "cognitive.cross_agent_runtime",
    "learning_agent.agent", "learning_agent.quiz_models", "learning_agent.practice_session",
    "learning_agent.practice_policy", "learning_agent.progress_tracker",
    "learning_agent.runtime", "learning_agent.executor", "learning_agent.content_generator",
    "learning_agent.resources.models", "learning_agent.remediation",
    "learning_agent.remediation_loop", "learning_agent.reassessment_processor",
    "orchestrator.query_router", "orchestrator.orchestrator_runtime",
    "coding_agent.models", "coding_agent.agent", "coding_agent.code_runner",
    "coding_agent.static_analyzer", "coding_agent.verified_exercises", "coding_agent.open_topic",
    "coding_agent.submission_controller", "coding_agent.integrated_workflow",
    "coding_agent.cacm_runtime", "coding_agent.code_review_engine",
    "coding_agent.ai_code_reviewer", "coding_agent.correction_verifier",
    "coding_agent.guided_review_coordinator", "coding_agent.agentic_review_coordinator",
    "coding_agent.progressive_hint_engine", "coding_agent.adaptive_hint_coordinator",
    "coding_agent.misconception_detector", "coding_agent.diagnostic_bridge",
    "research_agent.models", "research_agent.agent", "research_agent.research_workflow",
    "research_agent.abstract_quality_validator", "research_agent.autonomous_search",
    "research_agent.paper_summarizer", "research_agent.thematic_reviewer",
    "research_agent.methodology_comparator", "research_agent.research_gap_identifier",
    "research_agent.research_objective_generator", "research_agent.intelligent_planner",
    "research_agent.personalized_coordinator", "research_agent.cacm_runtime",
    "research_agent.semantic_ranker", "research_agent.relevance_ranker",
)


@lru_cache(maxsize=1)
def data_classes():
    result = {}
    for suffix in DATA_MODULES:
        module = import_module("app." + suffix)
        for cls in vars(module).values():
            if isinstance(cls, type) and is_dataclass(cls) and cls.__module__ == module.__name__:
                result[module.__name__ + "." + cls.__name__] = cls
    return result


def encode(value):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("Non-finite snapshot number.")
        return value
    if isinstance(value, datetime):
        return {"kind": "datetime", "value": value.isoformat()}
    if is_dataclass(value) and not isinstance(value, type):
        name = type(value).__module__ + "." + type(value).__name__
        if name not in data_classes():
            raise ValueError("Unsupported snapshot data class: " + name)
        result = {"kind": "data", "type": name,
                  "fields": {f.name: encode(getattr(value, f.name)) for f in fields(value)
                             if not (name == "app.research_agent.research_workflow.ResearchWorkflowResult"
                                     and f.name in {"requested_papers", "summary_sources", "stage_errors", "search_complete"}
                                     and not hasattr(value, f.name))}}
        # Existing dynamically attached completion ID must survive refresh.
        if hasattr(value, "_progress_completion_id"):
            result["completion_id"] = value._progress_completion_id
        return result
    if isinstance(value, (list, tuple, set)):
        return {"kind": type(value).__name__, "items": [encode(v) for v in value]}
    if isinstance(value, dict):
        return {"kind": "dict", "items": [[encode(k), encode(v)] for k, v in value.items()]}
    raise ValueError("Unsupported snapshot value: " + type(value).__name__)


def decode(value):
    if value is None or type(value) in (str, bool, int):
        return value
    if type(value) is float and math.isfinite(value):
        return value
    if not isinstance(value, dict):
        raise ValueError("Malformed snapshot value.")
    kind = value.get("kind")
    if kind == "datetime":
        return datetime.fromisoformat(value["value"])
    if kind in ("list", "tuple", "set"):
        factory = {"list": list, "tuple": tuple, "set": set}[kind]
        return factory(decode(v) for v in value["items"])
    if kind == "dict":
        return {decode(k): decode(v) for k, v in value["items"]}
    if kind == "data":
        cls = data_classes().get(value.get("type"))
        if cls is None:
            raise ValueError("Unknown snapshot data class.")
        raw = value["fields"]
        expected = {f.name for f in fields(cls)}
        legacy_additions = {
            "app.orchestrator.query_router.QueryRoute": {"research_mode", "coding_mode"},
            "app.research_agent.models.ResearchPaper": {"doi"},
            "app.research_agent.research_workflow.ResearchWorkflowResult": {
                "requested_papers", "summary_sources", "stage_errors", "search_complete"},
            "app.cognitive.evidence.LearningEvidence": {"evidence_id"},
            "app.learning_agent.quiz_models.QuizQuestion": {"question_id"},
            "app.research_agent.models.ResearchComprehensionQuestion": {"question_id"},
            "app.learning_agent.practice_session.PracticeSession": {"session_id", "pending_assessment_id"},
        }.get(value.get("type"), set())
        if set(raw) - expected or (expected - set(raw)) - legacy_additions:
            raise ValueError("Snapshot fields do not match the current data model.")
        arguments = {k: decode(v) for k, v in raw.items()}
        for name in expected - set(raw):
            if name.endswith("_id") and name != "pending_assessment_id":
                # Stable across repeated loads and repeated references to old data.
                arguments[name] = "legacy-" + hashlib.sha256(json.dumps(
                    {"type": value["type"], "fields": raw}, sort_keys=True).encode()).hexdigest()
        result = cls(**arguments)
        if "completion_id" in value:
            from app.learning_agent.practice_session import PracticeSession
            if not isinstance(result, PracticeSession) or not isinstance(value["completion_id"], str):
                raise ValueError("Invalid practice completion identifier.")
            result._progress_completion_id = value["completion_id"]
        return result
    raise ValueError("Unknown snapshot value kind.")
