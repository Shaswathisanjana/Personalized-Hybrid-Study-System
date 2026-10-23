from __future__ import annotations

from dataclasses import dataclass, field

from app.research_agent.paper_summarizer import (
    PaperSummary,
    SUMMARY_FIELDS,
    NOT_REPORTED,
)


@dataclass
class ComparisonCell:
    value: str
    source_quote: str = ""
    is_supported: bool = False


@dataclass
class PaperComparison:
    paper_index: int
    title: str
    authors: list[str]
    year: int | None
    source_url: str
    fields: dict[str, ComparisonCell] = field(
        default_factory=dict
    )


@dataclass
class MethodologyComparison:
    topic: str
    papers: list[PaperComparison] = field(
        default_factory=list
    )
    comparison_fields: tuple[str, ...] = SUMMARY_FIELDS
    source_scope: str = "abstract_only"


class MethodologyComparator:
    """
    Builds a structured comparison using validated
    fields from existing paper summaries.

    No additional LLM request is required.
    """

    def compare(
        self,
        topic: str,
        summaries: list[PaperSummary],
    ) -> MethodologyComparison:

        if not topic or not topic.strip():
            raise ValueError("topic cannot be empty")

        if len(summaries) < 2:
            raise ValueError(
                "At least two paper summaries are required"
            )

        result = MethodologyComparison(
            topic=topic.strip()
        )

        for index, summary in enumerate(summaries, start=1):

            paper = PaperComparison(
                paper_index=index,
                title=summary.title,
                authors=list(summary.authors),
                year=summary.year,
                source_url=summary.source_url,
            )

            for field_name in SUMMARY_FIELDS:

                value = getattr(summary, field_name)
                quote = summary.evidence_quotes.get(
                    field_name, ""
                )

                supported = (
                    isinstance(value, str)
                    and bool(value.strip())
                    and value != NOT_REPORTED
                    and isinstance(quote, str)
                    and bool(quote.strip())
                )

                if supported:
                    paper.fields[field_name] = ComparisonCell(
                        value=value,
                        source_quote=quote,
                        is_supported=True,
                    )
                else:
                    paper.fields[field_name] = ComparisonCell(
                        value=NOT_REPORTED,
                        source_quote="",
                        is_supported=False,
                    )

            result.papers.append(paper)

        return result

    @staticmethod
    def to_markdown(
        comparison: MethodologyComparison,
    ) -> str:
        """
        Converts the comparison into a readable
        Markdown table.
        """

        if not comparison.papers:
            return "No papers available for comparison."

        def clean(value: str) -> str:
            return str(value).replace("|", "\\|").replace(
                "\n", " "
            )

        headers = [
            "Comparison Field",
            *[
                clean(paper.title)
                for paper in comparison.papers
            ],
        ]

        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(
                ["---"] * len(headers)
            ) + " |",
        ]

        for field_name in comparison.comparison_fields:

            values = [
                field_name.replace("_", " ").title()
            ]

            for paper in comparison.papers:
                cell = paper.fields.get(field_name)

                values.append(
                    clean(cell.value)
                    if cell
                    else NOT_REPORTED
                )

            lines.append(
                "| " + " | ".join(values) + " |"
            )

        lines.append("")
        lines.append(
            "Source scope: Abstract-derived summaries only."
        )

        lines.append("")
        lines.append("Paper sources:")

        for paper in comparison.papers:
            lines.append(
                f"- {paper.title}: {paper.source_url}"
            )

        return "\n".join(lines)
