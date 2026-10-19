from __future__ import annotations

from dataclasses import dataclass

from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine

from app.research_agent.agent import (
    ResearchAgent,
    ResearchAction,
)

from app.research_agent.intelligent_planner import (
    IntelligentResearchPlanner,
    ResearchPlan,
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
    plan: ResearchPlan | None = None


class PersonalizedResearchCoordinator:
    """
    Connects intelligent research planning, academic research
    analysis and the shared CACM cognitive model.

    Generating research content does not update mastery.
    Only assessed comprehension is submitted to CACM.
    """

    def __init__(
        self,
        student: StudentCognitiveModel,
        cognitive_engine: CognitiveEngine,
        workflow: IntegratedResearchWorkflow | None = None,
        research_agent: ResearchAgent | None = None,
        planner: IntelligentResearchPlanner | None = None,
    ):

        self.student = student

        self.research_agent = (
            research_agent
            if research_agent is not None
            else ResearchAgent()
        )

        self.planner = (
            planner
            if planner is not None
            else IntelligentResearchPlanner(
                research_agent=self.research_agent
            )
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
        Create a cognitive-state-aware plan, then execute
        the existing academic research workflow.
        """

        # Read the REAL unresolved conflict state from shared CACM.
        # A caller-supplied flag must not manufacture a conflict.
        detected_conflict = self.cacm_runtime.cognitive_engine.has_conflict(
            user_id=self.student.user_id,
            concept_name=concept_name.strip(),
        )

        if has_active_conflict and not detected_conflict:
            raise ValueError(
                "Diagnostic research requires a genuine unresolved "
                "conflict in the shared CACM cognitive engine."
            )

        plan = self.planner.create_plan(
            student=self.student,
            topic=topic,
            concept_name=concept_name,
            has_active_conflict=detected_conflict,
        )

        workflow_kwargs = {
            "topic": plan.topic,
            "limit": limit,
            "papers": papers,
            "include_thematic_review": include_thematic_review,
        }

        # Manually supplied papers must never trigger online retrieval.
        # Only the real integrated workflow receives planned search queries.
        if (
            papers is None
            and isinstance(self.workflow, IntegratedResearchWorkflow)
        ):
            workflow_kwargs["search_queries"] = plan.search_queries

        research = self.workflow.run(**workflow_kwargs)

        return PersonalizedResearchResult(
            action=plan.action,
            research=research,
            plan=plan,
        )

    def submit_comprehension_evaluation(
        self,
        user_id: str,
        question: ResearchComprehensionQuestion,
        evaluation: ResearchComprehensionEvaluation,
    ) -> ResearchCACMOutcome:
        """
        Submit evaluated student comprehension to CACM.
        """

        return self.cacm_runtime.process_comprehension(
            user_id=user_id,
            question=question,
            evaluation=evaluation,
        )
