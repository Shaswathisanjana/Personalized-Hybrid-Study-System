from __future__ import annotations

from app.research_agent.streamlit_diagnostic import display_research_diagnostic

import streamlit as st
from app.persistence.streamlit_state import (
    checkpoint_page, checkpoint,
)

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
from app.research_agent.search_session import SearchLimits


@checkpoint_page
def display_advanced_research_page(student, orchestrator, *, student_workspace=False):
    """
    Advanced academic research page using the shared
    CACM student and cognitive engine.
    """

    st.title("Research papers and analysis" if student_workspace else "Advanced Research Agent")

    st.write(
        "Search academic papers and generate individual "
        "summaries, methodology comparisons, preliminary "
        "research opportunities, and a downloadable report."
    )

    st.info(
        "Topic-search analysis below uses available abstracts. The separate PDF collection "
        "analyzes extracted page text. Research opportunities require broader literature verification."
    )

    from app.research_agent.streamlit_search import display_topic_search
    display_topic_search(student)
    from app.research_agent.streamlit_collection import display_pdf_collection
    display_pdf_collection(student)
    from app.research_agent.streamlit_library import display_research_library
    display_research_library(student)
    st.subheader('Research synthesis and comprehension practice' if student_workspace
                 else 'Existing abstract-based research analysis')

    if "advanced_research_result" not in st.session_state:
        st.session_state.advanced_research_result = None

    if "advanced_research_action" not in st.session_state:
        st.session_state.advanced_research_action = None

    legacy_target_max = min(100, SearchLimits.from_environment().max_target)
    with st.form("advanced_research_form"):

        topic = st.text_input(
            "Research topic",
            placeholder="Deep Learning for Medical Image Classification",
            key="advanced_research_topic_input",
        )

        concept_name = st.text_input(
            "Learning concept to personalize",
            placeholder="Deep Learning",
            key="advanced_research_concept_input",
        )

        if legacy_target_max == 1:
            limit = 1
            st.caption('Number of papers: 1 (configured maximum).')
        else:
            limit = st.slider(
                "Number of papers",
                min_value=1,
                max_value=legacy_target_max,
                value=min(2, legacy_target_max),
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

            st.session_state.advanced_research_job = {
                'request': dict(topic=topic.strip(), concept_name=concept_name.strip(),
                                limit=limit, include_thematic_review=include_themes),
                'outcome': None, 'complete': False, 'applied': False,
            }
            execute_analysis_job(student, orchestrator)

    job = st.session_state.get('advanced_research_job')
    if job and not job.get('complete'):
        st.warning('Research analysis has unfinished work. Saved stages will be reused on retry.')
        if job.get('error'):
            st.caption(job['error'])
        if st.button('Retry unfinished research analysis', key='advanced_research_retry'):
            execute_analysis_job(student, orchestrator)

    result = st.session_state.advanced_research_result
    diagnostic_topics = [name for name in student.concepts
                         if orchestrator.cognitive_engine.has_conflict(student.user_id, name)]
    saved_concept = st.session_state.get('research_diagnostic_concept')
    if (saved_concept and saved_concept not in diagnostic_topics
            and (st.session_state.get('research_diagnostic_session') is not None
                 or st.session_state.get('research_diagnostic_outcome') is not None)):
        diagnostic_topics.append(saved_concept)
    if diagnostic_topics:
        selected = st.selectbox('Research conflict to assess', diagnostic_topics, key='research_other_conflict',
                                index=diagnostic_topics.index(saved_concept) if saved_concept in diagnostic_topics else 0,
                                disabled=st.session_state.get('research_diagnostic_session') is not None)
        display_research_diagnostic(selected, student, orchestrator)

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
            if student_workspace:
                with st.expander("Professor/Developer Debug — research decisions", expanded=False):
                    display_research_decisions(plan=plan, research=result)
            else:
                display_research_decisions(plan=plan, research=result)

        display_advanced_research_results(result)

        assessment_concept = st.session_state.get(
            'advanced_research_concept'
        )

        if action is not None and assessment_concept:
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


def execute_analysis_job(student, orchestrator):
    from app.research_agent.analysis_recovery import run_analysis_job
    from app.orchestrator.student_journey import StudentJourneyService
    coordinator = StudentJourneyService(student, orchestrator).research_coordinator(
        coordinator_factory=PersonalizedResearchCoordinator)
    try:
        with st.spinner('Processing unfinished research stages...'):
            run_analysis_job(st.session_state, coordinator, checkpoint)
    except Exception as exc:
        st.error('Research analysis stopped. Completed stages remain saved for explicit retry.')
        st.caption(str(exc))
