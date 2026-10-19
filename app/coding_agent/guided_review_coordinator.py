from dataclasses import dataclass

from app.coding_agent.ai_code_reviewer import (
    AICodeReviewer,
    AIReviewResult,
)
from app.coding_agent.correction_verifier import (
    CorrectionVerifier,
    CorrectionVerificationResult,
)
from app.coding_agent.code_runner import BehavioralTestCase


@dataclass
class GuidedCodeReviewResult:
    review: AIReviewResult
    verification: CorrectionVerificationResult | None
    correction_status: str
    educational_feedback: str


class GuidedCodeReviewCoordinator:
    """
    Connects AI code review with behavioral correction verification.

    AI-generated corrections are not student assessment evidence.
    This coordinator does not update CACM or student mastery.
    """

    def __init__(
        self,
        reviewer=None,
        verifier=None,
    ):
        self.reviewer = (
            reviewer
            if reviewer is not None
            else AICodeReviewer()
        )

        self.verifier = (
            verifier
            if verifier is not None
            else CorrectionVerifier()
        )

    def review_submission(
        self,
        code: str,
        problem_description: str = "",
        concept_name: str = "",
        test_cases: list[BehavioralTestCase] | None = None,
    ) -> GuidedCodeReviewResult:

        if test_cases is None:
            test_cases = []

        if not isinstance(test_cases, list):
            raise TypeError("test_cases must be a list.")

        if not all(
            isinstance(test, BehavioralTestCase)
            for test in test_cases
        ):
            raise TypeError(
                "Every test case must be a BehavioralTestCase."
            )

        review = self.reviewer.review(
            code=code,
            problem_description=problem_description,
            concept_name=concept_name,
        )

        corrected_code = review.corrected_code.strip()

        if not corrected_code:
            return GuidedCodeReviewResult(
                review=review,
                verification=None,
                correction_status="no_correction",
                educational_feedback=(
                    "The AI reviewer provided feedback but did not "
                    "supply a corrected solution. Use its hints to "
                    "improve your own code."
                ),
            )

        verification = self.verifier.verify(
            corrected_code=corrected_code,
            test_cases=test_cases,
        )

        if verification.all_tests_passed:
            status = "passed_supplied_tests"
            feedback = (
                "The suggested correction passed all supplied "
                "behavioral tests. This does not guarantee that "
                "it works for every possible input. Study the "
                "hints and try correcting your own solution."
            )

        elif not verification.syntax_valid:
            status = "syntax_failed"
            feedback = (
                "The AI-suggested correction contains a Python "
                "syntax error. It was not executed. Treat the "
                "suggestion as unverified."
            )

        elif not test_cases:
            status = "no_tests"
            feedback = (
                "The suggested correction has valid Python syntax, "
                "but no behavioral tests were supplied. Its "
                "correctness remains unverified."
            )

        elif verification.timed_out:
            status = "timed_out"
            feedback = (
                "Verification stopped because execution exceeded "
                "the time limit. This does not establish whether "
                "the suggested correction is correct."
            )

        else:
            status = "failed_supplied_tests"
            feedback = (
                "The suggested correction did not pass all "
                "supplied behavioral tests. Review the failed "
                "cases before relying on it."
            )

        return GuidedCodeReviewResult(
            review=review,
            verification=verification,
            correction_status=status,
            educational_feedback=feedback,
        )
