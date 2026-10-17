from __future__ import annotations

from dataclasses import dataclass

from app.research_agent.paper_summarizer import (
    PaperSummary,
    NOT_REPORTED,
)


@dataclass
class IndividualPaperOverview:
    title: str
    source_url: str
    simple_summary: str
    evidence_scope: str = "abstract_only"


class IndividualPaperOverviewBuilder:
    """
    Builds a beginner-friendly overview from an existing
    structured paper summary.

    It does not perform another LLM call or introduce
    information beyond the verified structured fields.
    """

    @staticmethod
    def build(
        summary: PaperSummary,
    ) -> IndividualPaperOverview:

        if not isinstance(summary, PaperSummary):
            raise TypeError(
                "Expected a PaperSummary object."
            )

        statements = []

        field_templates = [
            (
                "research_problem",
                "The paper addresses",
            ),
            (
                "proposed_method",
                "The proposed approach is",
            ),
            (
                "dataset",
                "The reported dataset is",
            ),
            (
                "evaluation_metrics",
                "The reported evaluation metrics are",
            ),
            (
                "key_findings",
                "The reported findings are",
            ),
            (
                "limitations",
                "The reported limitations are",
            ),
        ]

        for field_name, prefix in field_templates:

            value = str(
                getattr(summary, field_name)
            ).strip()

            quote = summary.evidence_quotes.get(
                field_name, ""
            ).strip()

            if (
                not value
                or value == NOT_REPORTED
                or not quote
            ):
                continue

            clean_value = value.rstrip(" .")

            statements.append(
                f"{prefix} {clean_value}."
            )

        if statements:
            overview = " ".join(statements)
        else:
            overview = (
                "The available abstract does not contain "
                "enough verified information to produce "
                "a meaningful individual paper overview. "
                "Please consult the original publication."
            )

        return IndividualPaperOverview(
            title=summary.title,
            source_url=summary.source_url,
            simple_summary=overview,
        )

    @classmethod
    def build_multiple(
        cls,
        summaries: list[PaperSummary],
    ) -> list[IndividualPaperOverview]:

        return [
            cls.build(summary)
            for summary in summaries
        ]
