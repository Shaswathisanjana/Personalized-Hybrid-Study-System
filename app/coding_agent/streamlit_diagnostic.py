import streamlit as st
from app.persistence.streamlit_state import (
    checkpoint_page, begin_assessment, finish_assessment,
)

from app.coding_agent.diagnostic_bridge import CodingDiagnosticBridge
from app.coding_agent.verified_exercises import VERIFIED_CONCEPTS


@checkpoint_page
def display_coding_diagnostic(student, orchestrator):
    """Display shared CACM diagnostic intervention for Coding Agent."""

    st.subheader("Cross-Agent Diagnostic Intervention")

    st.caption(
        "A diagnostic is available only when assessed evidence from "
        "different agents creates a genuine unresolved CACM conflict."
    )

    engine = orchestrator.cognitive_engine

    conflicted_concepts = [
        concept
        for concept in dict.fromkeys([*VERIFIED_CONCEPTS,
                                      *(state.concept_name for state in student.concepts.values())])
        if engine.has_conflict(
            user_id=student.user_id,
            concept_name=concept,
        )
    ]

    saved_session = st.session_state.get(
        "advanced_coding_diagnostic_session"
    )
    saved_result = st.session_state.get(
        "advanced_coding_diagnostic_result"
    )

    # Preserve the completed assessment even if it resolved
    # the last active conflict.
    if (
        saved_session is not None
        and saved_result is not None
        and saved_session.user_id == student.user_id
        and saved_session.concept_name not in conflicted_concepts
    ):
        conflicted_concepts = [
            *conflicted_concepts,
            saved_session.concept_name,
        ]

    if not conflicted_concepts:
        st.success(
            "No unresolved cross-agent conflicts were detected "
            "for the supported coding concepts."
        )
        return

    concept = st.selectbox(
        "Select a conflicted concept",
        conflicted_concepts,
        key="advanced_coding_diagnostic_concept",
    )

    conflicts = engine.get_conflicts(
        student.user_id,
        concept,
    )

    if conflicts:
        st.warning(
            f"CACM detected {len(conflicts)} unresolved "
            f"cross-agent conflict(s) for {concept}."
        )
    else:
        st.success(
            "No unresolved conflict remains for this concept. "
            "The completed diagnostic result is preserved below."
        )

    for conflict in conflicts:
        st.write(
            f"**{conflict.first_agent} vs {conflict.second_agent}** "
            f"| Difference: {conflict.difference:.2f} "
            f"| Severity: {conflict.severity}"
        )

    # Preserve one bridge and its completed-session cache across reruns.
    bridge = st.session_state.get(
        "advanced_coding_diagnostic_bridge"
    )

    if (
        bridge is None
        or bridge.student is not student
        or bridge.cognitive_engine is not engine
    ):
        bridge = CodingDiagnosticBridge(
            student=student,
            cognitive_engine=engine,
        )
        st.session_state.advanced_coding_diagnostic_bridge = bridge
        st.session_state.pop(
            "advanced_coding_diagnostic_session",
            None,
        )
        st.session_state.pop(
            "advanced_coding_diagnostic_result",
            None,
        )

    session = st.session_state.get(
        "advanced_coding_diagnostic_session"
    )

    if session is None or session.concept_name != concept:
        if st.button(
            "Generate Diagnostic Question",
            key="advanced_coding_generate_diagnostic",
        ):
            with st.spinner("Generating diagnostic question..."):
                try:
                    decision = bridge.start(concept)

                    st.session_state.advanced_coding_diagnostic_session = (
                        decision.diagnostic_session
                    )
                    st.session_state.pop(
                        "advanced_coding_diagnostic_result",
                        None,
                    )

                    st.rerun()

                except Exception as exc:
                    st.error(
                        f"Diagnostic question could not be generated: {exc}"
                    )

        return

    st.markdown("### Diagnostic Question")
    st.write(session.question.question)

    completed = st.session_state.get(
        "advanced_coding_diagnostic_result"
    )

    if completed is None:
        answer = st.text_area(
            "Your diagnostic answer",
            key="advanced_coding_diagnostic_answer",
            height=140,
        )

        if st.button(
            "Submit Diagnostic Answer",
            key="advanced_coding_submit_diagnostic",
            type="primary",
        ):
            if not answer.strip():
                st.warning("Please enter your answer.")
            else:
                with st.spinner("Evaluating diagnostic answer..."):
                    try:
                        begin_assessment("coding_diagnostic", {"answer": answer, "session": session})
                        outcome = bridge.submit_answer(
                            session=session,
                            answer=answer,
                        )

                        st.session_state.advanced_coding_diagnostic_result = (
                            outcome
                        )

                        finish_assessment()
                        st.rerun()

                    except Exception as exc:
                        st.error(
                            f"Diagnostic evaluation failed: {exc}"
                        )

        return

    st.divider()
    st.subheader("Diagnostic Results")

    evaluation = completed.resolution.diagnostic_outcome.evaluation

    st.metric(
        "Diagnostic Performance",
        f"{evaluation.performance:.0%}",
    )

    st.write("**Feedback:**", evaluation.feedback)

    if completed.resolution.diagnostic_outcome.conflict_resolved:
        st.success("CACM resolved the detected conflict.")
    elif completed.has_active_conflict:
        st.warning(
            "The conflict remains unresolved. "
            "Further assessed evidence may be necessary."
        )

    state = student.get_concept(concept)

    col1, col2, col3 = st.columns(3)

    col1.metric("Updated Mastery", f"{state.mastery:.0%}")
    col2.metric("Updated Confidence", f"{state.confidence:.0%}")
    col3.metric("Attempts", state.attempts)

    next_action = completed.next_coding_action

    st.info(
        f"Next Coding Agent action: {next_action.action_type} "
        f"| Recommended difficulty: {next_action.difficulty}"
    )

    st.caption(next_action.reason)

    st.caption(
        "This diagnostic uses the shared Cognitive Engine. "
        "Reopening the result does not submit new evidence."
    )
