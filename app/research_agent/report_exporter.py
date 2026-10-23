from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

from app.research_agent.paper_summarizer import SUMMARY_FIELDS
from app.research_agent.individual_paper_overview import IndividualPaperOverviewBuilder
from app.research_agent.research_workflow import ResearchWorkflowResult
from app.research_agent.methodology_comparator import MethodologyComparator
from app.research_agent.research_gap_identifier import ResearchGapIdentifier
from app.research_agent.research_objective_generator import ResearchObjectiveGenerator


class ResearchReportExporter:
    """
    Exports an integrated research workflow result
    into an evidence-linked Markdown report.
    """

    @staticmethod
    def build_markdown(
        result: ResearchWorkflowResult,
    ) -> str:

        if not isinstance(result, ResearchWorkflowResult):
            raise TypeError(
                "Expected a ResearchWorkflowResult"
            )

        lines = [
            "# Academic Research Analysis Report",
            "",
            f"**Topic:** {result.topic}",
            "",
            "**Generated (UTC):** "
            + datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            "",
            "**Evidence scope:** Available abstracts only",
            "",
            f"**Papers retrieved:** {len(result.papers)}",
            "",
            f"**Papers accepted:** {len(result.accepted_papers)}",
            "",
            f"**Papers excluded:** {len(result.excluded_papers)}",
            "",
            f"**Papers summarized:** {len(result.summaries)}",
            "",
            "### Abstract Quality Validation",
            "",
            "The following decisions use heuristic checks on "
            "retrieved abstracts. Exclusion does not imply "
            "that a publication is academically poor.",
            "",
        ]

        if getattr(result, "requested_papers", None) is not None:
            lines.extend([f"**Requested usable-paper target:** {result.requested_papers}", "",
                          "Availability and abstract quality can prevent this target from being met.", ""])
        lines.extend(["### Retrieved Source Manifest", ""])
        for index, paper in enumerate(result.papers, 1):
            lines.extend([f"- Source {index}: {paper.title}",
                          f"  - Provider: {paper.source or 'Not supplied'}",
                          f"  - Publication ID: {paper.paper_id or 'Not supplied'}",
                          f"  - URL: {paper.url or 'Not supplied'}"])
        if getattr(result, "stage_errors", {}):
            lines.extend(["", "### Unfinished Analysis", ""])
            for name, error in result.stage_errors.items():
                lines.append(f"- {name}: {error}")
        lines.append("")

        if result.excluded_papers:
            for paper, quality in result.excluded_papers:
                lines.extend([
                    f"**Excluded: {paper.title}**",
                    "",
                    f"- Status: {quality.status}",
                    f"- Reason: {quality.reason}",
                    f"- Retrieved abstract words: {quality.word_count}",
                    f"- Source: {paper.url}",
                    "",
                ])
        else:
            lines.extend([
                "No retrieved papers were excluded by the "
                "abstract-quality validator.",
                "",
            ])

        lines.extend([
            "---",
            "",
            "## 1. Structured Paper Summaries",
            "",
        ])

        if not result.summaries:
            lines.append(
                "No structured paper summaries available."
            )

        for index, summary in enumerate(
            result.summaries, start=1
        ):

            lines.extend([
                f"### Paper {index}: {summary.title}",
                "",
                "**Authors:** "
                + ", ".join(summary.authors),
                "",
                f"**Year:** {summary.year or 'Not reported'}",
                "",
                f"**Source:** {summary.source_url}",
                "",
            ])

            overview = IndividualPaperOverviewBuilder.build(
                summary
            )

            lines.extend([
                "**Simple Summary:**",
                "",
                overview.simple_summary,
                "",
                "**Detailed Structured Summary:**",
                "",
            ])

            for field_name in SUMMARY_FIELDS:

                value = getattr(summary, field_name)

                lines.extend([
                    "**"
                    + field_name.replace("_", " ").title()
                    + ":**",
                    "",
                    str(value),
                    "",
                ])

                quote = summary.evidence_quotes.get(
                    field_name, ""
                )

                if quote:
                    lines.extend([
                        "**Supporting abstract quotation:**",
                        "",
                        "> " + quote.replace(
                            "\n", " "
                        ),
                        "",
                    ])

        lines.extend([
            "---",
            "",
            "## 2. Thematic Literature Review",
            "",
        ])

        if result.thematic_review is None:
            lines.append(
                "Thematic review was not generated."
            )
        else:
            for theme in result.thematic_review.themes:

                lines.extend([
                    f"### {theme.name}",
                    "",
                    theme.description,
                    "",
                    f"**Coverage:** {theme.coverage}",
                    "",
                ])

                for evidence in theme.supporting_evidence:

                    lines.extend([
                        "- Paper: " + evidence.paper_title,
                        "  - Field: " + evidence.field_name,
                        "  - Finding: " + evidence.finding,
                        "  - Source: " + evidence.paper_url,
                        "  - Supporting quotation: "
                        + evidence.source_quote,
                        "",
                    ])

        lines.extend([
            "",
            "---",
            "",
            "## 3. Methodology Comparison",
            "",
        ])

        if result.comparison is None:
            lines.append(
                "Comparison unavailable: fewer than "
                "two summaries were available."
            )
        else:
            lines.append(
                MethodologyComparator.to_markdown(
                    result.comparison
                )
            )

        lines.extend([
            "",
            "---",
            "",
            "## 4. Research Opportunities",
            "",
        ])

        if result.gap_report is None:
            lines.append(
                "Research opportunity analysis unavailable."
            )
        else:
            lines.append(
                ResearchGapIdentifier.to_markdown(
                    result.gap_report
                )
            )

        lines.extend([
            "",
            "---",
            "",
            "## 5. Preliminary Research Objectives",
            "",
        ])

        if result.proposal is None:
            lines.append(
                "No research proposal available."
            )
        else:
            lines.append(
                ResearchObjectiveGenerator.to_markdown(
                    result.proposal
                )
            )

        lines.extend([
            "",
            "---",
            "",
            "## 6. Bibliography",
            "",
        ])

        if not result.papers:
            lines.append("No papers retrieved.")

        for index, paper in enumerate(
            result.papers, start=1
        ):

            authors = ", ".join(paper.authors)

            year = (
                str(paper.year)
                if paper.year is not None
                else "n.d."
            )

            lines.append(
                f"{index}. {authors} ({year}). "
                f"{paper.title}. {paper.url}"
            )

        lines.extend([
            "",
            "---",
            "",
            "## 7. Processing Warnings",
            "",
        ])

        if result.warnings:
            for warning in result.warnings:
                lines.append("- " + warning)
        else:
            lines.append(
                "No processing warnings were recorded."
            )

        lines.extend([
            "",
            "## Important Disclaimer",
            "",
            "This report uses available abstract-derived evidence. "
            "It is not a full-text systematic literature review. "
            "Proposed research opportunities require broader "
            "literature verification, and generated interpretations "
            "should be reviewed against the original publications.",
        ])

        return "\n".join(lines)

    @staticmethod
    def export(
        result: ResearchWorkflowResult,
        output_path: str,
    ) -> Path:

        path = Path(output_path)

        if path.suffix.lower() != ".md":
            raise ValueError(
                "Output file must use the .md extension"
            )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        content = ResearchReportExporter.build_markdown(
            result
        )

        path.write_text(
            content,
            encoding="utf-8",
        )

        return path
