from dataclasses import dataclass, field

from smera_app.coding_agent.code_review_engine import CodeReviewEngine
from smera_app.coding_agent.code_runner import (
    ControlledCodeRunner,
    BehavioralTestCase,
    BehavioralTestResult,
)


@dataclass
class CorrectionVerificationResult:
    syntax_valid: bool
    all_tests_passed: bool
    passed_count: int = 0
    total_count: int = 0
    timed_out: bool = False
    execution_error: str = ""
    message: str = ""
    test_results: list[BehavioralTestResult] = field(
        default_factory=list
    )


class CorrectionVerifier:
    """
    Checks suggested Python corrections against supplied tests.

    Passing all supplied tests is not proof of universal correctness.
    This module does not update CACM or assess student mastery.
    """

    def __init__(
        self,
        review_engine=None,
        code_runner=None,
    ):
        self.review_engine = (
            review_engine
            if review_engine is not None
            else CodeReviewEngine()
        )

        self.code_runner = (
            code_runner
            if code_runner is not None
            else ControlledCodeRunner(timeout_seconds=5.0)
        )

    def verify(
        self,
        corrected_code: str,
        test_cases: list[BehavioralTestCase],
    ) -> CorrectionVerificationResult:

        if not isinstance(corrected_code, str):
            raise TypeError("corrected_code must be a string.")

        if not isinstance(test_cases, list):
            raise TypeError("test_cases must be a list.")

        if not all(
            isinstance(test, BehavioralTestCase)
            for test in test_cases
        ):
            raise TypeError(
                "Every test case must be a BehavioralTestCase."
            )

        structural = self.review_engine.review(corrected_code)

        if not structural.syntax_valid:
            return CorrectionVerificationResult(
                syntax_valid=False,
                all_tests_passed=False,
                message=(
                    "Suggested correction failed Python syntax "
                    "inspection and was not executed."
                ),
            )

        if not test_cases:
            return CorrectionVerificationResult(
                syntax_valid=True,
                all_tests_passed=False,
                message=(
                    "Syntax is valid, but no behavioral tests "
                    "were supplied. Correction remains unverified."
                ),
            )

        run_result = self.code_runner.run_tests(
            code=corrected_code,
            test_cases=test_cases,
        )

        passed_count = run_result.passed_count
        total_count = run_result.total_count

        all_tests_passed = (
            total_count == len(test_cases)
            and total_count > 0
            and passed_count == total_count
            and not run_result.timed_out
            and not run_result.execution_error
        )

        if all_tests_passed:
            message = (
                "Suggested correction passed all supplied "
                "behavioral tests. This does not guarantee "
                "correctness for untested inputs."
            )
        else:
            message = (
                "Suggested correction did not pass all supplied "
                "behavioral tests. Review the reported failures."
            )

        return CorrectionVerificationResult(
            syntax_valid=True,
            all_tests_passed=all_tests_passed,
            passed_count=passed_count,
            total_count=total_count,
            timed_out=run_result.timed_out,
            execution_error=run_result.execution_error,
            message=message,
            test_results=run_result.tests,
        )
