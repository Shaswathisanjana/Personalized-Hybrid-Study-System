from __future__ import annotations

from dataclasses import dataclass, field

from app.research_agent.paper_summarizer import (
    PaperSummary,
    NOT_REPORTED,
)


@dataclass
class ResearchGapCandidate:
    paper_index: int
    paper_title: str
    paper_url: str
    reported_limitation: str
    supporting_quote: str
    opportunity: str
    classification: str = "Potential research opportunity"
    verification_status: str = "Requires broader literature verification"


@dataclass
class ResearchGapReport:
    topic: str
    papers_analyzed: int
    candidates: list[ResearchGapCandidate] = field(
        default_factory=list
    )
    notes: list[str] = field(default_factory=list)


class ResearchGapIdentifier:
    """
    Identifies source-backed limitations that may motivate
    further investigation.

    Does not claim that a limitation proves an unexplored
    research gap.
    """

    @staticmethod
    def identify(
        topic: str,
        summaries: list[PaperSummary],
    ) -> ResearchGapReport:

        if not isinstance(topic, str) or not topic.strip():
            raise ValueError("topic cannot be empty")

        if not summaries:
            raise ValueError(
                "At least one paper summary is required"
            )

        report = ResearchGapReport(
            topic=topic.strip(),
            papers_analyzed=len(summaries),
            notes=[
                "Candidates are derived only from explicitly "
                "reported, source-backed limitations.",
                "These are potential research opportunities, "
                "not proven gaps in the entire literature.",
                "Available evidence is abstract-derived; "
                "full-paper and broader literature checks are needed.",
            ],
        )

        for index, summary in enumerate(summaries, start=1):

            limitation = summary.limitations
            quote = summary.evidence_quotes.get(
                "limitations", ""
            )

            if (
                not isinstance(limitation, str)
                or not limitation.strip()
                or limitation.strip() == NOT_REPORTED
                or not isinstance(quote, str)
                or not quote.strip()
            ):
                continue

            report.candidates.append(
                ResearchGapCandidate(
                    paper_index=index,
                    paper_title=summary.title,
                    paper_url=summary.source_url,
                    reported_limitation=limitation.strip(),
                    supporting_quote=quote.strip(),
                    opportunity=(
                        "Investigate whether and how this "
                        "reported limitation can be addressed: "
                        + limitation.strip()
                    ),
                )
            )

        if not report.candidates:
            report.notes.append(
                "No explicitly supported limitations were "
                "available in the supplied summaries. "
                "This does not establish that no research gaps exist."
            )

        return report

    @staticmethod
    def to_markdown(
        report: ResearchGapReport,
    ) -> str:

        def clean(value: str) -> str:
            return str(value).replace("|", "\\|").replace(
                "\n", " "
            )

        lines = [
            "# Research Opportunity Report",
            "",
            f"Topic: {report.topic}",
            f"Papers analyzed: {report.papers_analyzed}",
            "",
        ]

        if not report.candidates:
            lines.append(
                "No source-backed limitation candidates available."
            )
        else:
            for number, candidate in enumerate(
                report.candidates, start=1
            ):
                lines.extend([
                    f"## Candidate {number}",
                    "",
                    f"Paper: {clean(candidate.paper_title)}",
                    "",
                    f"Source: {candidate.paper_url}",
                    "",
                    "Reported limitation: "
                    + clean(candidate.reported_limitation),
                    "",
                    "Supporting quotation: "
                    + clean(candidate.supporting_quote),
                    "",
                    "Possible investigation: "
                    + clean(candidate.opportunity),
                    "",
                    "Classification: "
                    + candidate.classification,
                    "",
                    "Verification: "
                    + candidate.verification_status,
                    "",
                ])

        lines.append("## Important Notes")
        lines.append("")

        for note in report.notes:
            lines.append("- " + note)

        return "\n".join(lines)
