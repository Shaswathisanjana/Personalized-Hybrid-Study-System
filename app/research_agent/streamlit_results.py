from __future__ import annotations

import streamlit as st

from app.research_agent.individual_paper_overview import (
    IndividualPaperOverviewBuilder,
)

from app.research_agent.paper_summarizer import (
    SUMMARY_FIELDS,
    NOT_REPORTED,
)

from app.research_agent.report_exporter import (
    ResearchReportExporter,
)


def display_advanced_research_results(result):
    """
    Display the integrated Research Agent workflow.

    This function only renders research content.
    It does not update the student's cognitive model.
    """

    st.subheader("Academic Research Analysis")

    st.caption(
        "Evidence scope: available abstracts. "
        "This is not a full-text systematic literature review."
    )

    st.write("**Research Topic:**", result.topic)
    if getattr(result, "requested_papers", None) is not None:
        st.caption(f"Requested target: {result.requested_papers} usable papers. "
                   "This is a target, not a guarantee of available abstracts or successful analysis.")
    if getattr(result, "stage_errors", {}):
        with st.expander("Unfinished analysis stages", expanded=True):
            for name, error in result.stage_errors.items():
                label = "Paper summary" if name.startswith("summary:") else name.replace("_", " ")
                st.warning(f"{label}: {error}")
    if result.papers:
        with st.expander("Retrieved source records", expanded=False):
            st.table([{"Title": paper.title, "Provider": paper.source or "Not supplied",
                       "Publication ID": paper.paper_id or "Not supplied", "Source URL": paper.url,
                       "Year": str(paper.year or "Not reported")} for paper in result.papers])

    st.metric(
        "Papers Retrieved",
        len(result.papers),
    )

    st.metric(
        "Papers Accepted",
        len(result.accepted_papers),
    )

    st.metric(
        "Papers Excluded",
        len(result.excluded_papers),
    )

    st.metric(
        "Papers Summarized",
        len(result.summaries),
    )

    if result.excluded_papers:
        with st.expander(
            "Excluded Papers and Reasons",
            expanded=False,
        ):
            st.caption(
                "These papers were retrieved but excluded from "
                "detailed analysis because their available "
                "abstracts did not pass the quality checks."
            )

            for paper, quality in result.excluded_papers:
                st.markdown(f"**{paper.title}**")
                st.write("Status:", quality.status.title())
                st.write("Reason:", quality.reason)

                if paper.url:
                    st.write("Source:", paper.url)

                st.divider()

    st.markdown("### 1. Individual Paper Summaries")

    if not result.summaries:
        st.info(
            "No structured paper summaries are available."
        )

    field_labels = {
        "research_problem": "Research Problem",
        "proposed_method": "Proposed Methodology",
        "dataset": "Dataset",
        "evaluation_metrics": "Evaluation Metrics",
        "key_findings": "Key Findings",
        "limitations": "Limitations",
    }

    for index, summary in enumerate(
        result.summaries,
        start=1,
    ):

        overview = IndividualPaperOverviewBuilder.build(
            summary
        )

        with st.expander(
            f"Paper {index}: {summary.title}",
            expanded=(index == 1),
        ):

            if summary.authors:
                st.write(
                    "**Authors:**",
                    ", ".join(summary.authors),
                )

            if summary.year:
                st.write(
                    "**Year:**",
                    summary.year,
                )

            if summary.source_url:
                st.link_button(
                    "Open Original Publication",
                    summary.source_url,
                )

            st.markdown("#### Simple Summary")

            st.write(
                overview.simple_summary
            )

            st.markdown(
                "#### Detailed Structured Summary"
            )

            for field_name in SUMMARY_FIELDS:

                label = field_labels.get(
                    field_name,
                    field_name.replace("_", " ").title(),
                )

                value = getattr(
                    summary,
                    field_name,
                    NOT_REPORTED,
                )

                st.markdown(
                    f"**{label}**"
                )

                st.write(value)

                quote = summary.evidence_quotes.get(
                    field_name,
                    "",
                )

                if quote:
                    st.caption(
                        "Supporting abstract quotation:"
                    )
                    st.markdown(
                        f"> {quote}"
                    )

                st.divider()

    exporter = ResearchReportExporter()

    markdown_report = exporter.build_markdown(
        result
    )

    st.download_button(
        label="Download Complete Research Report (.md)",
        data=markdown_report,
        file_name="academic_research_report.md",
        mime="text/markdown",
    )

    st.markdown("### 2. Thematic Literature Review")

    if result.thematic_review is None:
        st.info(
            "Thematic review was not generated."
        )
    else:
        for theme in result.thematic_review.themes:

            with st.expander(theme.name):

                st.write(theme.description)

                st.caption(
                    f"Evidence coverage: {theme.coverage}"
                )

                for item in theme.supporting_evidence:

                    st.write(
                        f"**{item.paper_title}**"
                    )

                    st.write(item.finding)

                    if item.source_quote:
                        st.markdown(
                            f"> {item.source_quote}"
                        )

    st.markdown("### 3. Methodology Comparison")

    if result.comparison is None:
        st.info(
            "At least two summarized papers are needed "
            "for methodology comparison."
        )
    else:
        from app.research_agent.methodology_comparator import (
            MethodologyComparator,
        )

        st.markdown(
            MethodologyComparator.to_markdown(
                result.comparison
            )
        )

    st.markdown("### 4. Research Opportunities")

    if result.gap_report is None:
        st.info(
            "Research opportunities were not generated."
        )
    else:
        from app.research_agent.research_gap_identifier import (
            ResearchGapIdentifier,
        )

        st.markdown(
            ResearchGapIdentifier.to_markdown(
                result.gap_report
            )
        )

    st.markdown("### 5. Preliminary Research Objectives")

    if result.proposal is None:
        st.info(
            "Preliminary research objectives were not generated."
        )
    else:
        from app.research_agent.research_objective_generator import (
            ResearchObjectiveGenerator,
        )

        st.markdown(
            ResearchObjectiveGenerator.to_markdown(
                result.proposal
            )
        )

    if result.warnings:

        st.markdown("### Processing Warnings")

        for warning in result.warnings:
            st.warning(warning)
