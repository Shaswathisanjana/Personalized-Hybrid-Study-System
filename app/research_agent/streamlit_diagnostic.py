from __future__ import annotations

import streamlit as st
from app.persistence.streamlit_state import (
    checkpoint_page, begin_assessment, finish_assessment,
)

from app.research_agent.diagnostic_bridge import (
    ResearchDiagnosticBridge,
)


@checkpoint_page
def display_research_diagnostic(
    concept_name,
    student,
    orchestrator,
):
    """
    Display an actual CACM diagnostic assessment when
    cross-agent evidence conflicts.

    Ordinary research comprehension remains separate.
    """

    engine = orchestrator.cognitive_engine

    has_conflict = engine.has_conflict(
        user_id=student.user_id,
        concept_name=concept_name,
    )

    st.divider()
    st.subheader("Cross-Agent Diagnostic Intervention")

    # Display completed diagnostic feedback before checking whether
    # the conflict still exists. A successful diagnostic may have
    # already removed the conflict from CACM.
    completed = st.session_state.get(
        "research_diagnostic_outcome"
    )
    completed_concept = st.session_state.get(
        "research_diagnostic_concept"
    )

    if completed is not None and completed_concept == concept_name:
        diagnostic = completed.diagnostic_outcome
        evaluation = diagnostic.evaluation

        st.success("Diagnostic assessment completed.")

        st.write(
            "**Diagnostic performance:**",
            f"{evaluation.performance:.2f}",
        )
        st.write(
            "**Evaluation feedback:**",
            evaluation.feedback,
        )

        if diagnostic.conflict_resolved:
            st.success(
                "CACM resolved the cross-agent cognitive conflict."
            )
        elif diagnostic.has_active_conflict:
            st.warning(
                "The conflict remains unresolved. Further diagnostic "
                "intervention may be required."
            )
        else:
            st.info(
                "No active conflict remains after diagnostic processing."
            )

        concept = student.get_concept(concept_name)

        st.markdown("#### Updated CACM State")
        st.write("**Mastery:**", f"{concept.mastery:.3f}")
        st.write("**Confidence:**", f"{concept.confidence:.3f}")
        st.write("**Attempts:**", concept.attempts)

        st.markdown("#### Learning Agent Replanning")
        st.write(
            "**Next recommended action:**",
            completed.next_action.action_type,
        )

        # Keep the completed result visible; do not offer the
        # same diagnostic session for another submission.
        return

    if not has_conflict:
        st.success(
            "No unresolved cross-agent cognitive conflict "
            "is currently detected for this concept."
        )
        return

    st.warning(
        "CACM detected contradictory assessment evidence "
        "from different agents. A diagnostic assessment "
        "can help resolve this disagreement."
    )

    if (
        st.session_state.get("research_diagnostic_bridge") is None
        or st.session_state.get("research_diagnostic_student_id")
        != student.user_id
        or st.session_state.get("research_diagnostic_engine")
        is not engine
    ):
        st.session_state.research_diagnostic_bridge = (
            ResearchDiagnosticBridge(
                student=student,
                cognitive_engine=engine,
            )
        )
        st.session_state.research_diagnostic_student_id = (
            student.user_id
        )
        st.session_state.research_diagnostic_engine = engine
        st.session_state.research_diagnostic_session = None
        st.session_state.research_diagnostic_concept = None
        st.session_state.research_diagnostic_outcome = None

    bridge = st.session_state.research_diagnostic_bridge

    session = st.session_state.get(
        "research_diagnostic_session"
    )

    if (
        session is not None
        and session.concept_name != concept_name
    ):
        session = None
        st.session_state.research_diagnostic_session = None
        st.session_state.research_diagnostic_outcome = None

    if session is None:

        if st.button(
            "Generate CACM Diagnostic Question",
            key="generate_research_diagnostic",
        ):
            try:
                with st.spinner(
                    "Preparing a diagnostic assessment..."
                ):
                    decision = bridge.start(concept_name)

                st.session_state.research_diagnostic_session = (
                    decision.diagnostic_session
                )
                st.session_state.research_diagnostic_concept = (
                    concept_name
                )
                st.session_state.research_diagnostic_outcome = None

                st.rerun()

            except Exception as exc:
                st.error(
                    "Could not generate the diagnostic assessment."
                )
                st.caption(
                    f"{type(exc).__name__}: {exc}"
                )

        return

    st.write(
        "**Concept:**",
        session.concept_name,
    )

    st.write(
        "**Difficulty:**",
        session.difficulty.title(),
    )

    st.markdown(
        f"**Diagnostic question:** {session.question.question}"
    )

    with st.form(
        "research_diagnostic_answer_form"
    ):
        answer = st.text_area(
            "Your diagnostic answer",
            placeholder="Explain your understanding...",
        )

        submitted = st.form_submit_button(
            "Submit Diagnostic Answer",
            type="primary",
        )

    if submitted:

        if not answer.strip():
            st.warning(
                "Please enter an answer before submitting."
            )
            return

        try:
            with st.spinner(
                "Evaluating diagnostic evidence through CACM..."
            ):
                begin_assessment("research_diagnostic", {"answer": answer, "session": session})
                outcome = bridge.submit_answer(
                    session=session,
                    answer=answer,
                )

            st.session_state.research_diagnostic_outcome = (
                outcome
            )

            # Prevent another submission of the same session.
            st.session_state.research_diagnostic_session = None

            finish_assessment()
            st.rerun()

        except Exception as exc:
            st.error(
                "Diagnostic assessment could not be completed."
            )
            st.caption(
                f"{type(exc).__name__}: {exc}"
            )
