from __future__ import annotations

from app.research_agent.models import (
    ResearchEvidenceItem,
    ResearchSynthesis,
)
from app.research_agent.paper_summarizer import (
    NOT_REPORTED,
    SUMMARY_FIELDS,
)
from app.research_agent.research_workflow import (
    ResearchWorkflowResult,
)


class ResearchAssessmentContextBuilder:
    """
    Converts source-supported research findings into
    material suitable for a comprehension assessment.

    This module does not evaluate students or update CACM.
    """

    def build(
        self,
        result: ResearchWorkflowResult,
    ) -> ResearchSynthesis:

        if not result.summaries:
            raise ValueError(
                "Cannot generate an assessment without "
                "research summaries."
            )

        evidence: list[ResearchEvidenceItem] = []

        for summary in result.summaries:

            for field_name in SUMMARY_FIELDS:

                value = str(
                    getattr(summary, field_name, "")
                ).strip()

                quote = str(
                    summary.evidence_quotes.get(
                        field_name,
                        "",
                    )
                ).strip()

                if not value or value == NOT_REPORTED:
                    continue

                if not quote:
                    continue

                evidence.append(
                    ResearchEvidenceItem(
                        claim=(
                            f"{field_name.replace('_', ' ').title()}: "
                            f"{value}\n"
                            f"Supporting source quote: {quote}"
                        ),
                        paper_title=summary.title,
                        paper_url=summary.source_url,
                        relevance=1.0,
                    )
                )

        if not evidence:
            raise ValueError(
                "No source-supported findings are available "
                "for a comprehension assessment."
            )

        answer = "\n\n".join(
            item.claim
            for item in evidence
        )

        return ResearchSynthesis(
            topic=result.topic,
            question=(
                "What do the available source-supported "
                "research findings establish about this topic?"
            ),
            answer=answer,
            evidence=evidence,
            papers_used=list(result.accepted_papers),
        )
