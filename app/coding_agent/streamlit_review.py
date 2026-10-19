import streamlit as st

from app.coding_agent.agentic_review_coordinator import (
    AgenticCodeReviewCoordinator,
)


def display_code_review_tab(student, orchestrator):
    st.subheader("Paste Code & AI Review")

    st.write(
        "Paste your Python code. The AI reviewer will identify possible "
        "problems, and the Coding Agent will use your shared CACM state "
        "to recommend an appropriate next learning action."
    )

    st.caption(
        "General code review does not automatically update CACM mastery. "
        "Only assessed student performance contributes assessment evidence."
    )

    code = st.text_area(
        "Paste your Python code",
        height=320,
        placeholder=(
            "def factorial(n):\\n"
            "    return n * factorial(n - 1)"
        ),
        key="advanced_coding_review_editor",
    )

    if st.button(
        "Review My Code",
        key="advanced_coding_review_button",
        type="primary",
    ):
        if not code.strip():
            st.warning("Please paste some Python code first.")
            return

        # Clear old feedback before attempting a new review.
        st.session_state.pop("advanced_coding_review_outcome", None)
        st.session_state.pop("advanced_coding_review_result", None)
        st.session_state.pop("advanced_coding_review_source", None)

        with st.spinner("AI Coding Agent is reviewing your code..."):
            try:
                coordinator = AgenticCodeReviewCoordinator(
                    student=student,
                    cognitive_engine=orchestrator.cognitive_engine,
                )
                outcome = coordinator.review_code(code)

                st.session_state.advanced_coding_review_outcome = outcome
                st.session_state.advanced_coding_review_source = code

            except Exception as exc:
                st.error(f"Code review could not be completed: {exc}")
                return

    outcome = st.session_state.get(
        "advanced_coding_review_outcome"
    )
    reviewed_code = st.session_state.get(
        "advanced_coding_review_source"
    )

    if outcome is None:
        return

    if reviewed_code != code:
        st.info(
            "Your code has changed since the last review. "
            "Click 'Review My Code' again for updated feedback."
        )
        return

    result = outcome.review

    st.divider()
    st.subheader("AI Review Results")
    st.write(result.summary)

    if result.learning_concept:
        st.info(
            f"Identified learning concept: {result.learning_concept}"
        )

    if result.issues:
        st.markdown("### Issues and Suggestions")

        for index, issue in enumerate(result.issues, start=1):
            with st.expander(
                f"Issue {index}: {issue.category}",
                expanded=True,
            ):
                if issue.line_number is not None:
                    st.write(f"Line: {issue.line_number}")

                st.write(f"**Explanation:** {issue.explanation}")
                st.write(f"**Hint:** {issue.hint}")
                st.write(f"**Suggested fix:** {issue.suggested_fix}")
    else:
        st.success(
            "The AI reviewer did not identify any issues. "
            "This is not proof that the code is fully correct."
        )

    if result.corrected_code.strip():
        st.markdown("### Suggested Corrected Code")
        st.code(result.corrected_code, language="python")
        st.warning(
            "This correction was suggested by AI. It has not "
            "been verified against behavioral tests."
        )

    st.divider()
    st.subheader("Coding Agent's Personalized Recommendation")

    if not outcome.practice_available:
        st.info(outcome.decision_reason)
        return

    action = outcome.recommended_action

    st.write(f"**Identified concept:** {outcome.identified_concept}")
    st.write(
        f"**Recommended action:** "
        f"{action.action_type.replace('_', ' ').title()}"
    )
    st.write(f"**Recommended difficulty:** {action.difficulty.title()}")
    st.write(f"**Why this action?** {action.reason}")

    st.caption(outcome.decision_reason)

    st.info(
        "Our current verified exercise bank contains introductory "
        "tasks. The agent's adaptive recommendation does not imply "
        "that a matching medium/hard exercise is already available."
    )

    if st.button(
        "Proceed to Targeted Practice",
        key="advanced_coding_review_to_practice",
        type="primary",
    ):
        st.session_state[
            "advanced_coding_target_concept"
        ] = outcome.identified_concept

        st.success(
            f"{outcome.identified_concept} has been transferred "
            "to Personalized Practice. Open the Personalized "
            "Practice tab to continue."
        )
