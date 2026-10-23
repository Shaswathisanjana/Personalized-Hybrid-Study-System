from __future__ import annotations

import streamlit as st
from app.persistence.streamlit_state import (
    checkpoint_page, begin_assessment, finish_assessment,
)

from app.research_agent.assessment_service import (
    ResearchAssessmentService,
)
from app.research_agent.personalized_coordinator import (
    PersonalizedResearchCoordinator,
)


@checkpoint_page
def display_research_assessment(
    result,
    action,
    concept_name,
    student,
    orchestrator,
):
    """
    Student comprehension assessment for the Advanced
    Research Agent.

    Only submitting an evaluated answer updates CACM.
    """

    st.divider()
    st.subheader("Research Comprehension Assessment")

    if not result.summaries:
        st.info(
            "No research summaries are available for assessment."
        )
        return

    if st.session_state.get("research_assessment_service") is None:
        coordinator = PersonalizedResearchCoordinator(
            student=student,
            cognitive_engine=orchestrator.cognitive_engine,
        )

        st.session_state.research_assessment_service = (
            ResearchAssessmentService(
                coordinator=coordinator,
            )
        )

    if "research_assessment_question" not in st.session_state:
        st.session_state.research_assessment_question = None

    if "research_assessment_completed" not in st.session_state:
        st.session_state.research_assessment_completed = False

    if "research_assessment_feedback" not in st.session_state:
        st.session_state.research_assessment_feedback = None

    service = st.session_state.research_assessment_service

    question = st.session_state.research_assessment_question

    if question is None:

        if st.button(
            "Generate Comprehension Question",
            key="generate_research_comprehension",
        ):

            try:
                with st.spinner(
                    "Generating a source-grounded question..."
                ):
                    question = service.generate_question(
                        result=result,
                        concept_name=concept_name,
                        difficulty=action.difficulty,
                    )

                st.session_state.research_assessment_question = (
                    question
                )

                st.session_state.research_assessment_completed = False
                st.session_state.research_assessment_feedback = None

                st.rerun()

            except Exception as exc:
                st.error(
                    "Could not generate a comprehension question."
                )
                st.caption(
                    f"{type(exc).__name__}: {exc}"
                )

        return

    st.write("**Concept:**", question.concept_name)
    st.write("**Difficulty:**", question.difficulty.title())

    st.markdown(
        f"**Question:** {question.question}"
    )

    if st.session_state.research_assessment_completed:

        feedback = st.session_state.research_assessment_feedback

        if feedback is not None:

            evaluation, outcome = feedback

            st.success("Assessment completed.")

            st.write(
                "**Performance:**",
                f"{evaluation.performance:.2f}",
            )

            st.write(
                "**Evaluation feedback:**",
                evaluation.feedback,
            )

            st.write(
                "**Reference explanation:**",
                question.explanation,
            )

            concept = student.get_concept(
                question.concept_name
            )

            st.markdown("#### Updated CACM State")

            st.write(
                "**Mastery:**",
                f"{concept.mastery:.3f}",
            )

            st.write(
                "**Confidence:**",
                f"{concept.confidence:.3f}",
            )

            st.write(
                "**Attempts:**",
                concept.attempts,
            )

            if outcome.has_active_conflict:
                st.warning(
                    "CACM detected an active cognitive conflict."
                )

        return

    with st.form("research_comprehension_answer_form"):

        answer = st.text_area(
            "Your answer",
            placeholder=(
                "Explain the concept in your own words..."
            ),
        )

        submitted = st.form_submit_button(
            "Submit Answer for Evaluation",
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
                "Evaluating comprehension and updating CACM..."
            ):

                begin_assessment("research", {"answer": answer, "question": question})
                evaluation, outcome = service.submit_answer(
                    user_id=student.user_id,
                    question=question,
                    answer=answer,
                )

            st.session_state.research_assessment_feedback = (
                evaluation,
                outcome,
            )

            st.session_state.research_assessment_completed = True

            finish_assessment()
            st.rerun()

        except Exception as exc:

            st.error(
                "Assessment could not be completed."
            )

            st.caption(
                f"{type(exc).__name__}: {exc}"
            )
