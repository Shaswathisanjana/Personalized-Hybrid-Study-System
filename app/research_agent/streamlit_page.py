from __future__ import annotations

from app.research_agent.streamlit_diagnostic import display_research_diagnostic

import streamlit as st

from app.research_agent.personalized_coordinator import (
    PersonalizedResearchCoordinator,
)
from app.research_agent.streamlit_results import (
    display_advanced_research_results,
)
from app.research_agent.streamlit_assessment import (
    display_research_assessment,
)
from app.research_agent.streamlit_decisions import (
    display_research_decisions,
)


def display_advanced_research_page(student, orchestrator):
    """
    Advanced academic research page using the shared
    CACM student and cognitive engine.
    """

    st.title("Advanced Research Agent")

    st.write(
        "Search academic papers and generate individual "
        "summaries, methodology comparisons, preliminary "
        "research opportunities, and a downloadable report."
    )

    st.info(
        "Analysis uses available abstracts, not complete "
        "paper PDFs. Research opportunities require "
        "broader literature verification."
    )

    if "advanced_research_result" not in st.session_state:
        st.session_state.advanced_research_result = None

    if "advanced_research_action" not in st.session_state:
        st.session_state.advanced_research_action = None

    with st.form("advanced_research_form"):

        topic = st.text_input(
            "Research topic",
            placeholder="Deep Learning for Medical Image Classification",
        )

        concept_name = st.text_input(
            "Learning concept to personalize",
            placeholder="Deep Learning",
        )

        limit = st.slider(
            "Number of papers",
            min_value=2,
            max_value=5,
            value=2,
        )

        include_themes = st.checkbox(
            "Generate thematic literature review",
            value=False,
            help=(
                "This requires an additional AI analysis call "
                "and may take longer."
            ),
        )

        submitted = st.form_submit_button(
            "Generate Research Analysis",
            type="primary",
        )

    if submitted:

        if not topic.strip() or not concept_name.strip():
            st.warning(
                "Enter both a research topic and a learning concept."
            )

        else:

            coordinator = PersonalizedResearchCoordinator(
                student=student,
                cognitive_engine=orchestrator.cognitive_engine,
            )

            try:

                with st.spinner(
                    "Searching papers and generating research analysis..."
                ):

                    outcome = coordinator.conduct_research(
                        topic=topic.strip(),
                        concept_name=concept_name.strip(),
                        limit=limit,
                        include_thematic_review=include_themes,
                    )

            except Exception as exc:

                st.error(
                    "Research analysis could not be completed."
                )

                st.caption(
                    f"{type(exc).__name__}: {exc}"
                )

            else:

                st.session_state.advanced_research_result = (
                    outcome.research
                )

                st.session_state.advanced_research_action = (
                    outcome.action
                )

                st.session_state.advanced_research_plan = (
                    outcome.plan
                )

                # A new research result needs a fresh assessment.
                st.session_state.advanced_research_concept = (
                    concept_name.strip()
                )
                st.session_state.research_assessment_service = None
                st.session_state.research_assessment_question = None
                st.session_state.research_assessment_completed = False
                st.session_state.research_assessment_feedback = None

    result = st.session_state.advanced_research_result

    if result is not None:

        action = st.session_state.advanced_research_action

        if action is not None:

            st.markdown("### CACM Personalization")

            st.write(
                "**Selected research action:**",
                action.action_type.replace("_", " ").title(),
            )

            st.write(
                "**Recommended difficulty:**",
                action.difficulty.title(),
            )

            st.caption(action.reason)

        plan = st.session_state.get(
            "advanced_research_plan"
        )

        if plan is not None:
            display_research_decisions(
                plan=plan,
                research=result,
            )

        display_advanced_research_results(result)

        assessment_concept = st.session_state.get(
            'advanced_research_concept'
        )

        if action is not None and assessment_concept:
            # Display the existing CACM diagnostic workflow
            # only when a real conflict exists or when
            # completed diagnostic feedback must be shown.
            if orchestrator.cognitive_engine.has_conflict(
                user_id=student.user_id,
                concept_name=assessment_concept,
            ) or (
                st.session_state.get("research_diagnostic_outcome")
                is not None
                and st.session_state.get(
                    "research_diagnostic_concept"
                ) == assessment_concept
            ):
                display_research_diagnostic(
                    concept_name=assessment_concept,
                    student=student,
                    orchestrator=orchestrator,
                )

            display_research_assessment(
                result=result,
                action=action,
                concept_name=assessment_concept,
                student=student,
                orchestrator=orchestrator,
            )

        st.caption(
            "Viewing or downloading research does not update "
            "student mastery. Only assessed comprehension "
            "can generate research evidence for CACM."
        )
