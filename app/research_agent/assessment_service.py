from __future__ import annotations

from app.research_agent.assessment_context import (
    ResearchAssessmentContextBuilder,
)
from app.research_agent.comprehension_generator import (
    ResearchComprehensionGenerator,
)
from app.research_agent.comprehension_evaluator import (
    ResearchComprehensionEvaluator,
)
from app.research_agent.models import (
    ResearchComprehensionQuestion,
    ResearchStudentAnswer,
)
from app.research_agent.personalized_coordinator import (
    PersonalizedResearchCoordinator,
)
from app.research_agent.research_workflow import (
    ResearchWorkflowResult,
)


class ResearchAssessmentService:
    """
    Connects verified research findings, comprehension
    assessment, and the shared CACM cognitive engine.

    Generating a question does not update mastery.
    Only a successfully evaluated answer is forwarded
    to CACM.
    """

    def __init__(
        self,
        coordinator: PersonalizedResearchCoordinator,
        generator=None,
        evaluator=None,
        context_builder=None,
    ):
        self.coordinator = coordinator
        self.generator = generator
        self.evaluator = evaluator
        self.context_builder = (
            context_builder
            if context_builder is not None
            else ResearchAssessmentContextBuilder()
        )

        self._submitted_question_ids: set[int] = set()

    def generate_question(
        self,
        result: ResearchWorkflowResult,
        concept_name: str,
        difficulty: str = "medium",
    ) -> ResearchComprehensionQuestion:

        synthesis = self.context_builder.build(result)

        if self.generator is None:
            self.generator = ResearchComprehensionGenerator()

        return self.generator.generate(
            synthesis=synthesis,
            concept_name=concept_name,
            difficulty=difficulty,
        )

    def submit_answer(
        self,
        user_id: str,
        question: ResearchComprehensionQuestion,
        answer: str,
    ):

        if not answer.strip():
            raise ValueError(
                "Enter an answer before submitting."
            )

        question_id = id(question)

        if question_id in self._submitted_question_ids:
            raise ValueError(
                "This assessment has already been submitted."
            )

        if user_id.strip() != self.coordinator.student.user_id:
            raise ValueError(
                "Assessment user does not match the shared student."
            )

        if self.evaluator is None:
            self.evaluator = ResearchComprehensionEvaluator()

        student_answer = ResearchStudentAnswer(
            user_id=user_id,
            question=question,
            answer=answer.strip(),
        )

        evaluation = self.evaluator.evaluate(
            student_answer
        )

        outcome = self.coordinator.submit_comprehension_evaluation(
            user_id=user_id,
            question=question,
            evaluation=evaluation,
        )

        self._submitted_question_ids.add(question_id)

        return evaluation, outcome
