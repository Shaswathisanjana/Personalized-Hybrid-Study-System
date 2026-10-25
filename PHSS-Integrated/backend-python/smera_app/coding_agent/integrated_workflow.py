from dataclasses import dataclass

from smera_app.cognitive.cognitive_engine import CognitiveEngine
from smera_app.cognitive.models import StudentCognitiveModel

from smera_app.coding_agent.agent import CodingAgent, CodingAction
from smera_app.coding_agent.task_generator import CodingTaskGenerator
from smera_app.coding_agent.evaluator import CodingEvaluator
from smera_app.coding_agent.cacm_runtime import (
    CodingCACMRuntime,
    CodingCACMOutcome,
)
from smera_app.coding_agent.guided_review_coordinator import (
    GuidedCodeReviewCoordinator,
    GuidedCodeReviewResult,
)
from smera_app.coding_agent.models import (
    CodingTask,
    CodingSubmission,
    CodingEvaluation,
)
from smera_app.coding_agent.code_runner import BehavioralTestCase


@dataclass
class CodingWorkflowResult:
    evaluation: CodingEvaluation
    cognitive_outcome: CodingCACMOutcome
    guided_review: GuidedCodeReviewResult | None = None


class IntegratedCodingWorkflow:
    """
    Coordinates the existing Coding Agent components.

    Only the evaluated STUDENT submission enters CACM.
    AI-generated corrections never become mastery evidence.
    """

    def __init__(
        self,
        student: StudentCognitiveModel,
        cognitive_engine: CognitiveEngine,
        coding_agent=None,
        task_generator=None,
        evaluator=None,
        guided_reviewer=None,
    ):
        if not isinstance(student, StudentCognitiveModel):
            raise TypeError(
                "student must be a StudentCognitiveModel."
            )

        if not isinstance(cognitive_engine, CognitiveEngine):
            raise TypeError(
                "cognitive_engine must be a CognitiveEngine."
            )

        self.student = student
        self.cognitive_engine = cognitive_engine

        self.coding_agent = (
            coding_agent
            if coding_agent is not None
            else CodingAgent()
        )

        self.task_generator = task_generator
        self.evaluator = evaluator
        self.guided_reviewer = guided_reviewer

        self.cacm_runtime = CodingCACMRuntime(
            cognitive_engine=cognitive_engine,
            student=student,
        )

    def choose_action(
        self,
        concept_name: str,
    ) -> CodingAction:
        concept_name = concept_name.strip()

        if not concept_name:
            raise ValueError(
                "concept_name cannot be empty."
            )

        has_conflict = self.cognitive_engine.has_conflict(
            self.student.user_id,
            concept_name,
        )

        return self.coding_agent.choose_action(
            student=self.student,
            concept_name=concept_name,
            has_active_conflict=has_conflict,
        )

    def generate_task(
        self,
        concept_name: str,
    ) -> tuple[CodingAction, CodingTask]:

        action = self.choose_action(concept_name)

        if self.task_generator is None:
            self.task_generator = CodingTaskGenerator()

        task = self.task_generator.generate(
            concept_name=action.concept_name,
            difficulty=action.difficulty,
        )

        return action, task

    def submit_student_code(
        self,
        submission: CodingSubmission,
        test_cases: list[BehavioralTestCase],
        include_guided_review: bool = False,
    ) -> CodingWorkflowResult:

        if not isinstance(submission, CodingSubmission):
            raise TypeError(
                "submission must be a CodingSubmission."
            )

        if submission.user_id != self.student.user_id:
            raise ValueError(
                "Submission user_id does not match "
                "the shared student model."
            )

        if not isinstance(test_cases, list) or not all(
            isinstance(test, BehavioralTestCase)
            for test in test_cases
        ):
            raise TypeError(
                "test_cases must contain BehavioralTestCase objects."
            )

        if self.evaluator is None:
            self.evaluator = CodingEvaluator()

        # Assess the student's original submission.
        evaluation = self.evaluator.evaluate(
            submission=submission,
            test_cases=test_cases,
        )

        # Submit only the student's assessed performance to CACM.
        cognitive_outcome = self.cacm_runtime.submit_evaluation(
            user_id=submission.user_id,
            concept_name=submission.task.concept_name,
            difficulty=submission.task.difficulty,
            evaluation=evaluation,
        )

        guided_review = None

        if include_guided_review:
            if self.guided_reviewer is None:
                self.guided_reviewer = GuidedCodeReviewCoordinator()

            guided_review = self.guided_reviewer.review_submission(
                code=submission.code,
                problem_description=submission.task.description,
                concept_name=submission.task.concept_name,
                test_cases=test_cases,
            )

        return CodingWorkflowResult(
            evaluation=evaluation,
            cognitive_outcome=cognitive_outcome,
            guided_review=guided_review,
        )
