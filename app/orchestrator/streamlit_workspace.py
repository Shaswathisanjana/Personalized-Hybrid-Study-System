"""Render actual existing activities on the student page, rather than route cards."""
import streamlit as st

from app.orchestrator.study_workspace import (
    validate_workspace, start_workspace, prepare_active, ensure_learning, advance_workspace,
)
from app.persistence.streamlit_state import checkpoint, persistence_rerun
from app.orchestrator.student_journey import StudentJourneyService


def render_workspace(state, display_learning_output):
    result = state.get("last_result")
    if result is None:
        return
    plan = validate_workspace(state)
    if plan is None:
        plan = start_workspace(state, result)
    st.subheader(plan["concept"])
    names = {"learning": "Learn and practise", "coding": "Coding practice", "research": "Research papers and analysis"}
    st.caption(" → ".join(names[s["agent"]] for s in plan["steps"]))
    with st.expander("Professor/Developer Debug — activity routing", expanded=False):
        st.caption("Routing details: " + result.route.reason)
        st.table([{"Activity": names[s["agent"]], "Status": s["status"].replace("_", " ")}
                  for s in plan["steps"]])
        # Compatibility/debug handoffs remain optional. Students use the actual
        # activity rendered below without navigating to an advanced page.
        from app.orchestrator.streamlit_journey import render_workflow_handoff
        for output in result.agent_results:
            if output.agent in {"coding", "research"} and isinstance(output.output, dict):
                if output.agent == "research" or StudentJourneyService.coding_concept(plan["concept"]):
                    render_workflow_handoff(output.output)
    if plan["index"] == len(plan["steps"]):
        st.success("You have reached the end of this study sequence. Only evaluated responses changed your cognitive state.")
        st.table([{"Activity": names[s["agent"]], "Status": s["status"].replace("_", " ")} for s in plan["steps"]])
        return
    try:
        step = prepare_active(state)
    except ValueError as exc:
        st.warning(str(exc))
        return
    agent = step["agent"]
    agent_names = {"learning": "Learning Agent", "coding": "Coding Agent", "research": "Research Agent"}
    st.caption(f"Handling this activity: {agent_names[agent]}")
    if agent == "learning":
        ensure_learning(state, checkpoint)
        if step["status"] in {"running", "error"}:
            st.warning(step["error"] or "Learning preparation was interrupted. Retry explicitly to continue.")
            if st.button("Retry learning preparation", key="journey_retry_learning"):
                ensure_learning(state, checkpoint, retry=True)
                persistence_rerun()
        else:
            output = next(r.output for r in result.agent_results if r.agent == "learning")
            display_learning_output(output=output, concept_name=plan["concept"], learning_context=plan["query"])
    elif agent == "coding":
        from app.cognitive.concept_identity import concept_id
        from app.coding_agent.streamlit_page import display_personalized_practice
        existing = state.get("advanced_coding_exercise")
        matches = existing is not None and concept_id(existing.task.concept_name) == concept_id(plan["concept"])
        auto_load = step["status"] == "pending" and not matches
        if auto_load:
            step["status"] = "running"
            checkpoint()
        elif matches:
            step["status"] = "ready"
        display_personalized_practice(state["student"], state["orchestrator"], auto_load=auto_load, student_workspace=True)
    elif plan.get("research_mode", "search") == "collection":
        st.write("Compare and analyze your saved papers. Select sources and process the available content below.")
        from app.research_agent.streamlit_collection import display_pdf_collection
        from app.research_agent.streamlit_library import display_research_library
        display_pdf_collection(state["student"])
        display_research_library(state["student"])
        step["status"] = "ready"
    else:
        if step["status"] == "pending":
            # The original query authorizes one bounded retrieval. Selection,
            # analysis and later pages remain explicit student decisions.
            step["status"] = "running"
            checkpoint()
            try:
                from app.research_agent.search_session import ResearchSearchSession
                search = ResearchSearchSession(state["_persistence_store"], state["student"].user_id)
                saved, _ = search.load()
                if saved is None:
                    search.start(plan["concept"], min(10, search.limits.max_target, search.limits.max_results))
                    search.fetch_next()
                step["status"] = "ready"
            except Exception:
                step.update(status="error", error="Initial retrieval was unavailable. Use the search controls to retry; earlier sources remain saved.")
            checkpoint()
        if step["status"] in {"running", "error"}:
            st.warning(step["error"] or "Retrieval was interrupted. Use the search controls to retry explicitly.")
        from app.research_agent.streamlit_page import display_advanced_research_page
        display_advanced_research_page(state["student"], state["orchestrator"], student_workspace=True)
    snapshot = StudentJourneyService(state["student"], state["orchestrator"]).observe(plan["concept"])
    st.caption(f"Evaluated attempts for this topic: {snapshot['attempts']}. Viewing content adds no mastery.")
    if snapshot["has_conflict"]:
        st.warning("Assessed evidence disagrees. Resolve it before moving to the next activity.")
        if agent != "research":
            from app.research_agent.streamlit_diagnostic import display_research_diagnostic
            display_research_diagnostic(plan["concept"], state["student"], state["orchestrator"])
    if st.button("Continue to next activity" if plan["index"] + 1 < len(plan["steps"]) else "Finish study sequence",
                 key="journey_next_activity", disabled=snapshot["has_conflict"]):
        advance_workspace(state)
        persistence_rerun()
