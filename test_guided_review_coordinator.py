from app.coding_agent.guided_review_coordinator import (
    GuidedCodeReviewCoordinator,
)
from app.coding_agent.ai_code_reviewer import AIReviewResult
from app.coding_agent.code_runner import BehavioralTestCase


def check(name, condition):
    assert condition, f"FAILED: {name}"
    print(f"PASS: {name}")


class FakeReviewer:
    def __init__(self, corrected_code):
        self.corrected_code = corrected_code
        self.calls = 0

    def review(
        self,
        code,
        problem_description="",
        concept_name="",
    ):
        self.calls += 1

        return AIReviewResult(
            summary="Review completed.",
            issues=[],
            corrected_code=self.corrected_code,
            learning_concept=concept_name,
            correction_verified=False,
        )


student_code = (
    "def factorial(n):\n"
    "    if n == 1:\n"
    "        return 1\n"
    "    return n * factorial(n + 1)"
)

corrected_code = (
    "def factorial(n):\n"
    "    if n <= 1:\n"
    "        return 1\n"
    "    return n * factorial(n - 1)"
)

incorrect_correction = (
    "def factorial(n):\n"
    "    return n + 1"
)

test_cases = [
    BehavioralTestCase(
        test_name="Factorial zero",
        function_name="factorial",
        args=[0],
        expected_output=1,
    ),
    BehavioralTestCase(
        test_name="Factorial three",
        function_name="factorial",
        args=[3],
        expected_output=6,
    ),
    BehavioralTestCase(
        test_name="Factorial five",
        function_name="factorial",
        args=[5],
        expected_output=120,
    ),
]


# TEST 1: Correct AI suggestion passes supplied tests
reviewer = FakeReviewer(corrected_code)
coordinator = GuidedCodeReviewCoordinator(reviewer=reviewer)

result = coordinator.review_submission(
    code=student_code,
    problem_description="Calculate factorial.",
    concept_name="Recursion",
    test_cases=test_cases,
)

check(
    "Corrected solution verified against supplied tests",
    result.correction_status == "passed_supplied_tests"
    and result.verification is not None
    and result.verification.all_tests_passed
    and result.verification.passed_count == 3,
)


# TEST 2: AI review itself does not claim verification
check(
    "AI review remains independently unverified",
    result.review.correction_verified is False
    and reviewer.calls == 1,
)


# TEST 3: Incorrect AI suggestion fails verification
coordinator = GuidedCodeReviewCoordinator(
    reviewer=FakeReviewer(incorrect_correction)
)

result = coordinator.review_submission(
    code=student_code,
    concept_name="Recursion",
    test_cases=test_cases,
)

check(
    "Incorrect correction rejected",
    result.correction_status == "failed_supplied_tests"
    and result.verification is not None
    and not result.verification.all_tests_passed,
)


# TEST 4: Missing behavioral tests
coordinator = GuidedCodeReviewCoordinator(
    reviewer=FakeReviewer(corrected_code)
)

result = coordinator.review_submission(
    code=student_code,
    concept_name="Recursion",
    test_cases=[],
)

check(
    "Missing tests do not verify correction",
    result.correction_status == "no_tests"
    and result.verification is not None
    and not result.verification.all_tests_passed,
)


# TEST 5: AI reviewer supplies no correction
coordinator = GuidedCodeReviewCoordinator(
    reviewer=FakeReviewer("")
)

result = coordinator.review_submission(
    code=student_code,
    concept_name="Recursion",
    test_cases=test_cases,
)

check(
    "No correction handled safely",
    result.correction_status == "no_correction"
    and result.verification is None,
)


# TEST 6: Invalid test cases rejected
reviewer = FakeReviewer(corrected_code)
coordinator = GuidedCodeReviewCoordinator(reviewer=reviewer)

try:
    coordinator.review_submission(
        code=student_code,
        test_cases=["invalid"],
    )
except TypeError:
    rejected = True
else:
    rejected = False

check(
    "Invalid test cases rejected before AI review",
    rejected and reviewer.calls == 0,
)


print("\nALL SIX GUIDED CODE REVIEW TESTS PASSED.")
