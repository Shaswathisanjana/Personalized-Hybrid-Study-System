from __future__ import annotations

from dataclasses import dataclass

from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine

from app.research_agent.agent import (
    ResearchAgent,
    ResearchAction,
)

from app.research_agent.research_workflow import (
    IntegratedResearchWorkflow,
    ResearchWorkflowResult,
)

from app.research_agent.models import (
    ResearchPaper,
    ResearchComprehensionQuestion,
    ResearchComprehensionEvaluation,
)

from app.research_agent.cacm_runtime import (
    ResearchCACMRuntime,
    ResearchCACMOutcome,
)


@dataclass
class PersonalizedResearchResult:
    action: ResearchAction
    research: ResearchWorkflowResult


class PersonalizedResearchCoordinator:
    """
    Connects the Research Agent decision layer, academic
    research workflow and shared CACM cognitive model.

    Research content generation does NOT update mastery.
    Only assessed comprehension is sent into CACM.
    """

    def __init__(
        self,
        student: StudentCognitiveModel,
        cognitive_engine: CognitiveEngine,
        workflow: IntegratedResearchWorkflow | None = None,
        research_agent: ResearchAgent | None = None,
    ):

        self.student = student

        self.research_agent = (
            research_agent
            if research_agent is not None
            else ResearchAgent()
        )

        self.workflow = (
            workflow
            if workflow is not None
            else IntegratedResearchWorkflow()
        )

        self.cacm_runtime = ResearchCACMRuntime(
            cognitive_engine=cognitive_engine,
            student=student,
        )

    def conduct_research(
        self,
        topic: str,
        concept_name: str,
        limit: int = 5,
        has_active_conflict: bool = False,
        papers: list[ResearchPaper] | None = None,
        include_thematic_review: bool = True,
    ) -> PersonalizedResearchResult:
        """
        Select a personalized research action and execute
        the academic paper-analysis workflow.
        """

        action = self.research_agent.choose_action(
            student=self.student,
            concept_name=concept_name,
            has_active_conflict=has_active_conflict,
        )

        research = self.workflow.run(
            topic=topic,
            limit=limit,
            papers=papers,
            include_thematic_review=include_thematic_review,
        )

        return PersonalizedResearchResult(
            action=action,
            research=research,
        )

    def submit_comprehension_evaluation(
        self,
        user_id: str,
        question: ResearchComprehensionQuestion,
        evaluation: ResearchComprehensionEvaluation,
    ) -> ResearchCACMOutcome:
        """
        Send assessed student comprehension into CACM.
        This is the only cognitive-update operation here.
        """

        return self.cacm_runtime.process_comprehension(
            user_id=user_id,
            question=question,
            evaluation=evaluation,
        )
