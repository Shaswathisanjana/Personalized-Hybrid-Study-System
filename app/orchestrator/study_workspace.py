"""Owner-scoped, resumable activity sequencing; no cognitive updates of its own."""
from uuid import uuid4

from app.cognitive.concept_identity import concept_id, clean_concept_name
from app.orchestrator.student_journey import StudentJourneyService


def validate_workspace(state):
    plan = state.get("journey_workspace")
    if plan is None:
        return None
    if plan.get("user_id") != state["student"].user_id:
        raise ValueError("This study sequence belongs to another student.")
    steps = plan.get("steps")
    if (not isinstance(steps, list) or not 1 <= len(steps) <= 3
            or any(s.get("agent") not in {"learning", "coding", "research"} for s in steps)
            or type(plan.get("index")) is not int or not 0 <= plan["index"] <= len(steps)):
        raise ValueError("Invalid saved study sequence.")
    clean_concept_name(plan["concept"])
    if plan.get("research_mode", "search") not in {"search", "collection"}:
        raise ValueError("Invalid research activity mode.")
    statuses = {"pending", "running", "ready", "error", "assessed", "visited_without_assessment"}
    if (len({s["agent"] for s in steps}) != len(steps)
            or not isinstance(plan.get("query"), str) or not isinstance(plan.get("request_id"), str)
            or any(s.get("status") not in statuses or type(s.get("prepared")) is not bool
                   or not isinstance(s.get("error"), str)
                   or not (s.get("baseline") is None or (type(s["baseline"]) is int and s["baseline"] >= 0))
                   for s in steps)):
        raise ValueError("Invalid saved activity state.")
    return plan


def evidence_count(state, agent, concept):
    return sum(e.source_agent == agent and concept_id(e.concept_name) == concept_id(concept)
               for e in state["orchestrator"].cognitive_engine.evidence_store.get_all_evidence())


def start_workspace(state, result):
    """Save the plan before any deferred content action. Existing work stays saved."""
    agents = list(dict.fromkeys(result.route.selected_agents))
    if not agents or len(agents) > 3 or any(a not in {"learning", "coding", "research"} for a in agents):
        raise ValueError("The request did not identify a supported activity.")
    plan = dict(
        user_id=state["student"].user_id, request_id=str(uuid4()), query=result.query,
        concept=clean_concept_name(result.route.concept), index=0,
        research_mode=getattr(result.route, "research_mode", "search"),
        steps=[dict(agent=a, status="pending", prepared=False, baseline=None, error="") for a in agents])
    validate_workspace({"student": state["student"], "journey_workspace": plan})
    state["journey_workspace"] = plan
    return plan


def prepare_active(state):
    """Bind an activity to shared state; do not generate/assess code or papers."""
    plan = validate_workspace(state)
    if plan is None or plan["index"] == len(plan["steps"]):
        return None
    step = plan["steps"][plan["index"]]
    if step["prepared"]:
        return step
    concept, agent = plan["concept"], step["agent"]
    step["baseline"] = evidence_count(state, agent, concept)
    if agent == "coding":
        from app.coding_agent.open_topic import normalize_topic
        normalized = normalize_topic(concept)
        curated = StudentJourneyService.coding_concept(normalized)
        state["advanced_coding_free_topic"] = "" if curated else normalized
        if curated:
            state["advanced_coding_concept"] = curated
        # Do not change a saved language choice silently. The existing coding UI
        # explicitly blocks unsupported runtimes before execution.
    elif agent == "research":
        state["advanced_research_topic_input"] = concept
        state["advanced_research_concept_input"] = concept
        state["research_search_" + state["student"].user_id + "_topic"] = concept
    step["prepared"] = True
    return step


def ensure_learning(state, checkpoint=lambda: None, *, retry=False):
    """Checkpoint before provider work; interrupted/error stages require explicit retry."""
    plan = validate_workspace(state)
    step = prepare_active(state)
    if step is None or step["agent"] != "learning":
        return
    if step["status"] == "ready" or (step["status"] in {"running", "error"} and not retry):
        return
    result = state["last_result"]
    index = next(i for i, r in enumerate(result.agent_results) if r.agent == "learning")
    existing = result.agent_results[index]
    if existing.success and not (isinstance(existing.output, dict) and existing.output.get("kind") == "study_workflow"):
        step["status"] = "ready"  # Existing embedded runtime already generated this output.
        return
    step.update(status="running", error="")
    checkpoint()
    try:
        outcome = state["orchestrator"]._run_learning(state["student"], plan["concept"])
        if not outcome.success:
            raise ValueError("Learning content unavailable")
        result.agent_results[index] = outcome
        step["status"] = "ready"
        tracker = state.get("learning_progress_tracker")
        if tracker:
            tracker.start_topic(user_id=state["student"].user_id, topic_name=plan["concept"])
    except Exception:
        step.update(status="error", error="Learning content could not be prepared. Saved assessments are preserved; retry explicitly.")
    checkpoint()


def advance_workspace(state):
    plan = validate_workspace(state)
    step = prepare_active(state)
    if step is None:
        return
    service = StudentJourneyService(state["student"], state["orchestrator"])
    if service.observe(plan["concept"])["has_conflict"]:
        raise ValueError("Resolve the genuine cognitive conflict before continuing the sequence.")
    # Moving between screens is never an assessment. Use an honest visited label
    # unless new, real evidence for this activity/topic exists after entry.
    step["status"] = ("assessed" if evidence_count(state, step["agent"], plan["concept"]) > step["baseline"]
                      else "visited_without_assessment")
    plan["index"] += 1
