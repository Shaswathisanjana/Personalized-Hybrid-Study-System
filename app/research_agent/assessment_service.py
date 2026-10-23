from __future__ import annotations

from app.cognitive.assessment_transaction import assessment, once
from dataclasses import asdict
import hashlib
import json

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

        self._submitted_question_ids: set[str] = set()

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
        *, resume: bool = False,
    ):

        if not answer.strip():
            raise ValueError(
                "Enter an answer before submitting."
            )

        question_id = question.question_id
        fields = asdict(question)
        legacy_fields = {k: v for k, v in fields.items() if k != "question_id"}
        compatible_ids = {question_id, hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest(),
            hashlib.sha256(json.dumps(legacy_fields, sort_keys=True).encode()).hexdigest()}
        if compatible_ids & self._submitted_question_ids and not resume:
            raise ValueError("This assessment has already been submitted.")

        if user_id.strip() != self.coordinator.student.user_id:
            raise ValueError(
                "Assessment user does not match the shared student."
            )

        engine = self.coordinator.cacm_runtime.cognitive_engine
        request = ResearchStudentAnswer(user_id, question, answer.strip())
        identity = "research:" + question_id
        if compatible_ids & self._submitted_question_ids and (user_id, identity) not in engine.assessment_records:
            raise ValueError("This completed legacy assessment cannot be submitted again.")
        record = assessment(engine, self.coordinator.student, identity, request)
        def evaluate():
            if self.evaluator is None:
                self.evaluator = ResearchComprehensionEvaluator()
            return self.evaluator.evaluate(request)
        evaluation = once(engine, record, "evaluation", evaluate)
        outcome = once(engine, record, "cognitive_outcome", lambda:
            self.coordinator.submit_comprehension_evaluation(user_id=user_id,
                question=question, evaluation=evaluation, evidence_id=identity))
        self._submitted_question_ids.add(question_id)
        return evaluation, outcome
