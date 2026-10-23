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
    requested_papers: int | None = None
    summary_sources: dict[str, PaperSummary] = field(default_factory=dict)
    stage_errors: dict[str, str] = field(default_factory=dict)
    search_complete: bool = False


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

    def run(self, topic, limit=5, papers=None, include_thematic_review=True,
            search_queries=None, resume_result=None, on_checkpoint=None):
        from app.research_agent.analysis_execution import run_workflow
        return run_workflow(self, topic, limit, papers, include_thematic_review,
                            search_queries, resume_result, on_checkpoint)
