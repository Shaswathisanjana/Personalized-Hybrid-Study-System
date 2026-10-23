"""Study planning UI; only explicitly submitted answers create evidence."""
import streamlit as st

from app.learning_agent.study_planner import LearningStudyPlanner
from app.learning_agent.diagnostic_bridge import LearningDiagnosticBridge
from app.persistence.streamlit_state import (
    begin_assessment, finish_assessment, persistence_rerun,
)


def render_learning_diagnostic(student, orchestrator, concept_name):
    state = st.session_state
    engine = orchestrator.cognitive_engine
    st.markdown("#### Learning diagnostic")
    st.write(f"Resolve conflicting evidence for **{concept_name}**.")
    bridge = state.get("learning_diagnostic_bridge")
    if bridge is None or bridge.student is not student or bridge.cognitive_engine is not engine:
        bridge = LearningDiagnosticBridge(student, engine, orchestrator.learning_runtime)
        state.learning_diagnostic_bridge = bridge
    outcome = state.get("learning_diagnostic_outcome")
    if outcome is not None:
        diagnostic = outcome.diagnostic_outcome
        st.write(diagnostic.evaluation.feedback)
        st.write("Conflict resolved." if diagnostic.conflict_resolved else
                 "Conflicting evidence still requires assessment." if diagnostic.has_active_conflict
                 else "No active conflict remains.")
        st.caption(f"Next action: {outcome.next_action.action_type.replace('_', ' ')}")
    session = state.get("learning_diagnostic_session")
    if session is None:
        if not engine.has_conflict(student.user_id, concept_name):
            return
        if st.button("Generate learning diagnostic", key="learning_plan_generate_diagnostic"):
            try:
                state.learning_diagnostic_session = bridge.start(concept_name)
                state.learning_diagnostic_outcome = None
            except Exception as exc:
                st.error(f"The diagnostic could not be generated: {exc}")
                return
            persistence_rerun()
        return
    st.write(session.question.question)
    with st.form("learning_plan_diagnostic_" + session.session_id):
        answer = st.text_area("Your diagnostic answer")
        submitted = st.form_submit_button("Submit learning diagnostic")
    if submitted:
        if not answer.strip():
            st.warning("Enter an answer before submitting.")
            return
        try:
            begin_assessment("learning_diagnostic", {"session": session, "answer": answer.strip()})
            state.learning_diagnostic_outcome = bridge.submit_answer(session, answer.strip())
            state.learning_diagnostic_session = None
            finish_assessment()
        except Exception as exc:
            st.error(f"The diagnostic is saved for recovery: {exc}")
            return
        persistence_rerun()


def open_planned_step(student, orchestrator, step):
    """Keep the current activity until generation has succeeded."""
    from app.orchestrator.orchestrator_runtime import OrchestratorResult, AgentExecutionResult
    from app.orchestrator.query_router import QueryRoute
    experience = orchestrator.learning_runtime.get_planned_learning_experience(student, step)
    query = f"{step.purpose.title()} {step.topic_name}"
    route = QueryRoute(query, step.topic_name, ["learn"], ["learning"], True, step.reason)
    state = st.session_state
    for name in ("practice_session", "practice_feedback", "practice_summary", "practice_concept",
                 "practice_context", "practice_last_outcome", "last_answered_question", "last_student_answer"):
        state[name] = None
    state.waiting_for_next_question = False
    state.last_result = OrchestratorResult(query, route, [AgentExecutionResult("learning", True, experience)])
    state.last_query = query
    state.learning_progress_tracker.start_topic(student.user_id, step.topic_name)


def render_study_plan(student, orchestrator):
    state = st.session_state
    planner = LearningStudyPlanner()
    with st.expander("My Study Plan", expanded=False):
        topics = [topic.name for topic in planner.bank.all_topics()]
        goal = state.get("learning_goal")
        with st.form("learning_plan_goal_form"):
            selected = st.selectbox("Study goal", topics + ["Custom topic"],
                                    index=topics.index(goal) if goal in topics else len(topics) if goal else 0,
                                    key="learning_plan_goal_choice")
            custom = st.text_input("Custom study goal", value=goal if goal and goal not in topics else "",
                                   max_chars=200, key="learning_plan_custom_goal")
            save = st.form_submit_button("Save study goal")
        if save:
            chosen = custom.strip() if selected == "Custom topic" else selected
            if not chosen:
                st.warning("Enter a custom topic.")
            else:
                state.learning_goal = chosen
                persistence_rerun()
        if not goal:
            st.info("Save a goal to see a study path and personalized revision suggestions.")
            return
        plan = planner.create_plan(student, orchestrator.cognitive_engine, goal)
        st.write(f"**Goal: {plan.goal_topic}**")
        st.caption("The plan updates after assessments. Readiness uses current mastery and confidence estimates; "
                   "seven-day revision suggestions are prototype scheduling rules. Viewing content never increases mastery.")
        if plan.custom_goal:
            st.caption("Prerequisites for this custom topic are not in the topic bank.")
        step = plan.recommended
        if step:
            st.markdown(f"**Recommended: {step.purpose.title()} {step.topic_name} ({step.difficulty})**")
            st.write(step.reason)
            practice = state.get("practice_session")
            active = practice is not None and not practice.is_complete
            diagnostic_active = state.get("learning_diagnostic_session") is not None
            if step.purpose == "diagnostic":
                if not diagnostic_active:
                    if state.get("learning_diagnostic_concept") != step.topic_name:
                        state.learning_diagnostic_outcome = None
                    state.learning_diagnostic_concept = step.topic_name
            else:
                if active or diagnostic_active:
                    st.caption("Finish the current assessment or use Restart Current Activity before opening another lesson.")
                if st.button("Open recommended learning activity", key="learning_plan_open",
                             disabled=active or diagnostic_active):
                    try:
                        with st.spinner("Preparing your learning activity..."):
                            open_planned_step(student, orchestrator, step)
                    except Exception as exc:
                        st.error(f"The activity could not be prepared: {exc}")
                    else:
                        persistence_rerun()
        if plan.goal_steps:
            st.write("Path to your goal")
            st.table([{"Topic": s.topic_name, "Action": s.purpose.title(),
                       "Prerequisites to assess": ", ".join(s.blocked_by) or "Ready to start"}
                      for s in plan.goal_steps])
        else:
            st.success("Current assessed estimates meet this goal's readiness criteria.")
        if plan.revisions:
            st.write("Revision and reassessment suggestions")
            for suggestion in plan.revisions:
                st.write(f"- {suggestion.topic_name}: {suggestion.purpose} — {suggestion.reason}")
        if plan.next_topics:
            st.write("Other topics with assessed prerequisites")
            st.write(", ".join(s.topic_name for s in plan.next_topics))
        diagnostic_concept = state.get("learning_diagnostic_concept")
        if diagnostic_concept:
            render_learning_diagnostic(student, orchestrator, diagnostic_concept)
        if state.get("practice_session") is not None:
            session = state.practice_session
            st.caption(f"Current session: {session.questions_completed}/{session.max_questions} questions answered.")
        st.markdown("#### Completed learning sessions")
        history = planner.completed_sessions(student, orchestrator.cognitive_engine)
        if history:
            st.table([{"Topic": session.concept_name, "Completed": str(session.completed_at),
                       "Questions": summary.questions_completed,
                       "Assessment score": f"{summary.average_performance:.0%}"}
                      for session, summary in history])
        else:
            st.caption("No detailed completed sessions are saved yet. Earlier aggregate progress remains in My Learning Progress.")
