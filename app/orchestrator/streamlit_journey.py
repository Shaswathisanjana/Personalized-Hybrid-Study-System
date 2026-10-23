"""Common student-facing navigation and shared evidence across all three pages."""
import streamlit as st
from app.orchestrator.student_journey import StudentJourneyService, request_navigation
from app.persistence.streamlit_state import persistence_rerun


def handoff_button(state, agent, concept, label, key, *, query="", diagnostic=False, disabled=False):
    if st.button(label, key=key, disabled=disabled):
        request_navigation(state, agent, concept, query=query, diagnostic=diagnostic)
        persistence_rerun()


def render_workflow_handoff(output):
    if output.get("user_id") != st.session_state.student.user_id:
        st.error("This saved workflow request belongs to another student.")
        return
    agent, concept = output["agent"], output["concept"]
    st.write(f"**{concept}** — continue with " +
             ("verified coding practice and assessment." if agent == "coding" else
              "source-grounded research, saved analysis and comprehension assessment."))
    handoff_button(st.session_state, agent, concept,
                   "Open coding practice" if agent == "coding" else "Open research analysis",
                   "journey_routed_" + agent, query=output.get("query", ""))


def render_student_journey(state, *, student_workspace=False):
    with st.expander("Professor/Developer Debug — shared state" if student_workspace else "Continue studying", expanded=False):
        current = state.get("journey_topic") or state.get("learning_goal")
        if not current:
            result = state.get("last_result")
            current = result.route.concept if result else ""
        if "journey_topic_draft" not in state:
            state["journey_topic_draft"] = current
        with st.form("journey_topic_form"):
            concept = st.text_input("Topic to continue across activities",
                                    key="journey_topic_draft", max_chars=200)
            submitted = st.form_submit_button("Use this study topic")
        if submitted and concept.strip():
            state["journey_topic"] = concept.strip()
            persistence_rerun()
        if not current:
            st.caption("Choose a topic here or start a study request to continue it across activities.")
            return
        service = StudentJourneyService(state["student"], state["orchestrator"])
        snapshot = service.observe(current)
        st.write(f"**Shared study topic: {current}**")
        st.caption(f"Assessed attempts: {snapshot['attempts']}. Viewing or switching activities never adds evidence.")
        if snapshot["mastery"] is not None and snapshot["attempts"] > 0:
            st.write(f"Mastery estimate: {snapshot['mastery']:.0%} · Evidence confidence: {snapshot['confidence']:.0%}")
        else:
            st.caption("No assessed understanding is recorded for this topic yet.")
        if snapshot["evidence_sources"]:
            st.write("Recorded assessment sources: " + ", ".join(
                f"{source}: {count}" for source, count in snapshot["evidence_sources"].items()))
        if snapshot["has_conflict"]:
            st.warning("Assessed evidence disagrees. Resolve the conflict before choosing normal progression.")
            handoff_button(state, "research", current, "Resolve conflicting evidence", "journey_resolve",
                           diagnostic=True)
        st.table([{"Activity": label, "Next action": snapshot[agent].action_type.replace("_", " "),
                   "Difficulty": snapshot[agent].difficulty, "Reason": snapshot[agent].reason}
                  for agent, label in (("learning", "Learn"), ("coding", "Code"), ("research", "Research"))])
        handoff_button(state, "learning", current, "Continue learning", "journey_learn")
        handoff_button(state, "coding", current, "Continue coding practice", "journey_code",
                       disabled=not snapshot["coding_available"])
        if not snapshot["coding_available"]:
            st.caption("This shortcut opens the curated bank. Use the main study query for generated practice on custom Python topics.")
        handoff_button(state, "research", current, "Continue research", "journey_research")
        st.caption("Existing exercises, answers and analysis remain saved. A handoff prepares the next workflow; "
                   "generating a lesson, loading an exercise or starting analysis remains an explicit action.")
