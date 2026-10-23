import hashlib
from dataclasses import dataclass

from app.coding_agent.integrated_workflow import IntegratedCodingWorkflow
from app.coding_agent.models import CodingSubmission
from app.coding_agent.verified_exercises import VerifiedCodingExercise


@dataclass
class CodingSubmissionRecord:
    submission_id: str
    result: object


class CodingSubmissionController:
    """
    Controls assessed coding submissions.

    The caller must retain this controller for the current
    loaded exercise, rather than recreating it on every
    Streamlit rerun.
    """

    def __init__(
        self,
        workflow: IntegratedCodingWorkflow,
        exercise: VerifiedCodingExercise,
    ):
        if not isinstance(workflow, IntegratedCodingWorkflow):
            raise TypeError(
                "workflow must be an IntegratedCodingWorkflow."
            )

        if not isinstance(exercise, VerifiedCodingExercise):
            raise TypeError(
                "exercise must be a VerifiedCodingExercise."
            )

        if not exercise.test_cases:
            raise ValueError(
                "Assessed coding exercises require behavioral tests."
            )

        self.workflow = workflow
        self.exercise = exercise
        self.records = {}
        self.in_progress = set()

    def _submission_id(self, code: str) -> str:
        if not isinstance(code, str):
            raise TypeError("Student code must be a string.")

        identity = (
            self.workflow.student.user_id,
            self.exercise.task.concept_name,
            self.exercise.task.title,
            self.exercise.task.difficulty,
            code,
        )

        # Generated packages can share a title/difficulty but have different tests.
        # Keep existing curated receipt IDs compatible with saved assessments.
        if getattr(self.exercise, "package_id", ""):
            identity += (self.exercise.package_id,)

        return hashlib.sha256(
            repr(identity).encode("utf-8")
        ).hexdigest()

    def submit(self, code: str) -> tuple[CodingSubmissionRecord, bool]:
        """
        Returns (record, is_new_submission).

        An identical previously completed submission returns
        its cached result without updating CACM again.
        """

        if not isinstance(code, str) or not code.strip():
            raise ValueError(
                "Please write Python code before submitting."
            )

        submission_id = self._submission_id(code)

        if submission_id in self.records:
            return self.records[submission_id], False

        if submission_id in self.in_progress:
            raise RuntimeError(
                "This submission is already being evaluated."
            )

        self.in_progress.add(submission_id)

        try:
            submission = CodingSubmission(
                user_id=self.workflow.student.user_id,
                task=self.exercise.task,
                code=code,
            )

            # The existing workflow evaluates the student's
            # ORIGINAL code and sends that evaluation to CACM.
            #
            # Guided AI review is deliberately separate.
            result = self.workflow.submit_student_code(
                submission=submission,
                test_cases=self.exercise.test_cases,
                include_guided_review=False,
                assessment_id="coding:" + submission_id,
            )

            record = CodingSubmissionRecord(
                submission_id=submission_id,
                result=result,
            )

            self.records[submission_id] = record

            return record, True

        finally:
            self.in_progress.discard(submission_id)
