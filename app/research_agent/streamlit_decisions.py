from __future__ import annotations

import streamlit as st

from app.research_agent.intelligent_planner import ResearchPlan
from app.research_agent.research_workflow import ResearchWorkflowResult


def display_research_decisions(
    plan: ResearchPlan,
    research: ResearchWorkflowResult,
) -> None:
    """
    Displays the Research Agent's planning and search decisions.

    This is read-only: displaying results never updates CACM.
    """

    st.subheader("Research Agent Decision Dashboard")

    st.markdown("**Selected research strategy**")
    st.write(plan.action.action_type.replace("_", " ").title())

    st.markdown("**Assessment status**")

    if plan.is_new_concept:
        st.info(
            "This concept has no recorded assessment attempts. "
            "The initial mastery estimate is not treated as "
            "measured student knowledge."
        )
    else:
        st.write("Previously assessed concept.")

    st.markdown("**Why the agent selected this strategy**")
    st.write(plan.planning_reason)

    st.markdown("**Research goal**")
    st.write(plan.research_goal)

    st.markdown("**Planned research focus**")

    for item in plan.analysis_focus:
        st.write(f"- {item}")

    st.markdown("**Planned search queries**")

    for index, query in enumerate(plan.search_queries, start=1):
        st.write(f"{index}. {query}")

    st.divider()

    st.markdown("**Autonomous search history**")

    if not research.search_attempts:
        st.caption(
            "No autonomous search attempts were recorded. "
            "The workflow may have used manually supplied papers "
            "or its original single-search mode."
        )
        return

    for index, attempt in enumerate(
        research.search_attempts,
        start=1,
    ):
        with st.expander(
            f"Search attempt {index}: {attempt.query}",
            expanded=True,
        ):
            col1, col2 = st.columns(2)

            col1.metric(
                "Retrieved papers",
                attempt.retrieved_count,
            )

            col2.metric(
                "Usable unique papers so far",
                attempt.usable_count,
            )

            st.write(attempt.reason)

    st.caption(
        "Search decisions are based on abstract availability "
        "and minimum text-quality checks, not a scientific "
        "ranking of academic paper quality."
    )
