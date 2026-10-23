from __future__ import annotations

from dataclasses import dataclass, field

from app.research_agent.research_gap_identifier import (
    ResearchGapReport,
)


@dataclass
class ProposedResearchDirection:
    number: int
    objective: str
    research_question: str
    rationale: str
    source_paper: str
    source_url: str
    supporting_quote: str
    status: str = "Proposed direction - not a validated research gap"


@dataclass
class ResearchProposal:
    topic: str
    directions: list[ProposedResearchDirection] = field(
        default_factory=list
    )
    notes: list[str] = field(default_factory=list)


class ResearchObjectiveGenerator:
    """
    Creates preliminary objectives and questions from
    source-backed research opportunity candidates.

    This module does not claim that an opportunity is
    novel or that its proposed objective is achievable.
    """

    @staticmethod
    def generate(
        report: ResearchGapReport,
    ) -> ResearchProposal:

        if not isinstance(report, ResearchGapReport):
            raise TypeError(
                "Expected a ResearchGapReport"
            )

        proposal = ResearchProposal(
            topic=report.topic,
            notes=[
                "These objectives and questions are preliminary proposals.",
                "A reported limitation does not establish an unexplored gap.",
                "Broader literature review and feasibility checks are required.",
            ],
        )

        for candidate in report.candidates:

            limitation = candidate.reported_limitation.strip()
            quote = candidate.supporting_quote.strip()

            if not limitation or not quote:
                continue

            number = len(proposal.directions) + 1

            proposal.directions.append(
                ProposedResearchDirection(
                    number=number,
                    objective=(
                        "Investigate possible approaches to address "
                        "the following reported limitation: "
                        + limitation
                    ),
                    research_question=(
                        "What approaches could address the "
                        "following reported limitation, and "
                        "how could their effectiveness be evaluated? "
                        + limitation
                    ),
                    rationale=(
                        "This proposed direction is motivated by "
                        "a limitation explicitly reported in "
                        "the cited source."
                    ),
                    source_paper=candidate.paper_title,
                    source_url=candidate.paper_url,
                    supporting_quote=quote,
                )
            )

        if not proposal.directions:
            proposal.notes.append(
                "No supported research opportunities were supplied; "
                "no objectives or questions were generated."
            )

        return proposal

    @staticmethod
    def to_markdown(
        proposal: ResearchProposal,
    ) -> str:

        lines = [
            "# Preliminary Research Proposal",
            "",
            f"Topic: {proposal.topic}",
            "",
        ]

        if not proposal.directions:
            lines.append(
                "No evidence-supported directions available."
            )

        for direction in proposal.directions:

            lines.extend([
                f"## Proposed Direction {direction.number}",
                "",
                "**Research Objective:**",
                direction.objective,
                "",
                "**Research Question:**",
                direction.research_question,
                "",
                "**Rationale:**",
                direction.rationale,
                "",
                "**Supporting Paper:**",
                direction.source_paper,
                "",
                "**Source URL:**",
                direction.source_url,
                "",
                "**Supporting Quotation:**",
                direction.supporting_quote,
                "",
                "**Status:**",
                direction.status,
                "",
            ])

        lines.extend([
            "## Important Notes",
            "",
        ])

        for note in proposal.notes:
            lines.append("- " + note)

        return "\n".join(lines)
