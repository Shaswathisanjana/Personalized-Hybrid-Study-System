from __future__ import annotations

from dataclasses import dataclass, field

from app.research_agent.models import ResearchPaper
from app.research_agent.abstract_quality_validator import (
    AbstractQualityValidator,
    AbstractQualityResult,
)
from app.research_agent.paper_search import AcademicPaperSearch
from app.research_agent.autonomous_search import (
    AutonomousResearchSearcher,
    SearchAttempt,
)
from app.research_agent.paper_summarizer import (
    PaperSummary,
    StructuredPaperSummarizer,
)
from app.research_agent.thematic_reviewer import (
    ThematicLiteratureReviewer,
    ThematicReview,
)
from app.research_agent.methodology_comparator import (
    MethodologyComparator,
    MethodologyComparison,
)
from app.research_agent.research_gap_identifier import (
    ResearchGapIdentifier,
    ResearchGapReport,
)
from app.research_agent.research_objective_generator import (
    ResearchObjectiveGenerator,
    ResearchProposal,
)


@dataclass
class ResearchWorkflowResult:
    topic: str
    papers: list[ResearchPaper] = field(default_factory=list)
    accepted_papers: list[ResearchPaper] = field(default_factory=list)
    excluded_papers: list[tuple[ResearchPaper, AbstractQualityResult]] = field(default_factory=list)
    summaries: list[PaperSummary] = field(default_factory=list)
    thematic_review: ThematicReview | None = None
    comparison: MethodologyComparison | None = None
    gap_report: ResearchGapReport | None = None
    proposal: ResearchProposal | None = None
    warnings: list[str] = field(default_factory=list)
    source_scope: str = "abstract_only"
    search_attempts: list[SearchAttempt] = field(default_factory=list)


class IntegratedResearchWorkflow:
    """
    Coordinates academic search and evidence-grounded
    research analysis.

    This is a research-content workflow. It does not
    replace the CACM-aware ResearchAgent decision layer.
    """

    def __init__(
        self,
        search_service=None,
        summarizer=None,
        thematic_reviewer=None,
    ):
        self.search_service = search_service
        self.summarizer = summarizer
        self.thematic_reviewer = thematic_reviewer

        self.comparator = MethodologyComparator()
        self.gap_identifier = ResearchGapIdentifier()
        self.objective_generator = ResearchObjectiveGenerator()

    def run(
        self,
        topic: str,
        limit: int = 5,
        papers: list[ResearchPaper] | None = None,
        include_thematic_review: bool = True,
        search_queries: list[str] | None = None,
    ) -> ResearchWorkflowResult:

        if not isinstance(topic, str) or not topic.strip():
            raise ValueError("Research topic cannot be empty")

        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")

        result = ResearchWorkflowResult(topic=topic.strip())

        # A supplied paper list allows offline testing.
        # An empty supplied list is treated as empty input,
        # not as permission to start a network search.
        if papers is not None:
            result.papers = list(papers)

        elif search_queries is not None:
            searcher = AutonomousResearchSearcher(
                search_service=self.search_service,
                max_attempts=3,
            )

            refined = searcher.search(
                queries=search_queries,
                limit=limit,
                target_usable_papers=min(2, limit),
            )

            result.papers = list(refined.papers)
            result.search_attempts = list(refined.attempts)
            result.warnings.extend(refined.warnings)

        else:
            search = (
                self.search_service
                if self.search_service is not None
                else AcademicPaperSearch()
            )

            search_result = search.search(
                query=result.topic,
                limit=limit,
            )

            result.papers = list(search_result.papers)

            result.warnings.extend(
                search_result.provider_errors
            )

        if not result.papers:
            result.warnings.append(
                "No research papers were available for analysis."
            )
            return result

        validator = AbstractQualityValidator()

        for paper in result.papers:
            quality = validator.validate(
                abstract=paper.abstract,
                title=paper.title,
            )

            if quality.is_usable:
                result.accepted_papers.append(paper)
            else:
                result.excluded_papers.append((paper, quality))
                result.warnings.append(
                    f"Excluded paper '{paper.title}': {quality.reason}"
                )

        if not result.accepted_papers:
            result.warnings.append(
                'No papers passed abstract quality validation. '
                'Detailed analysis was not performed.'
            )
            return result

        summarizer = (
            self.summarizer
            if self.summarizer is not None
            else StructuredPaperSummarizer()
        )

        result.summaries = summarizer.summarize_multiple(
            result.accepted_papers
        )

        if not result.summaries:
            result.warnings.append(
                "No structured summaries were produced."
            )
            return result

        # A thematic review uses Gemini. Its failure should
        # not erase successfully completed analysis.
        if include_thematic_review:
            try:
                reviewer = (
                    self.thematic_reviewer
                    if self.thematic_reviewer is not None
                    else ThematicLiteratureReviewer()
                )

                result.thematic_review = reviewer.review(
                    topic=result.topic,
                    summaries=result.summaries,
                )

            except Exception as exc:
                result.warnings.append(
                    "Thematic review was unavailable: "
                    + str(exc)
                )

        # A comparison requires at least two summaries.
        if len(result.summaries) >= 2:
            result.comparison = self.comparator.compare(
                topic=result.topic,
                summaries=result.summaries,
            )
        else:
            result.warnings.append(
                "At least two summaries are required "
                "for methodology comparison."
            )

        result.gap_report = self.gap_identifier.identify(
            topic=result.topic,
            summaries=result.summaries,
        )

        result.proposal = self.objective_generator.generate(
            result.gap_report
        )

        return result
