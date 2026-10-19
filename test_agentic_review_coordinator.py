from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine

from app.coding_agent.ai_code_reviewer import AIReviewResult
from app.coding_agent.agentic_review_coordinator import (
    AgenticCodeReviewCoordinator,
)


class FakeReviewer:
    def __init__(self, concept):
        self.concept = concept

    def review(self, code):
        return AIReviewResult(
            summary="The code needs improvement.",
            issues=[],
            corrected_code="",
            learning_concept=self.concept,
        )


student = StudentCognitiveModel(user_id="agentic_review_test")
engine = CognitiveEngine()

coordinator = AgenticCodeReviewCoordinator(
    student=student,
    cognitive_engine=engine,
    reviewer=FakeReviewer("Recursion"),
)

before = student.get_concept("Recursion")
mastery_before = before.mastery
attempts_before = before.attempts

result = coordinator.review_code(
    "def factorial(n): return n * factorial(n - 1)"
)

assert result.identified_concept == "Recursion"
assert result.practice_available is True
assert result.recommended_action is not None
assert result.recommended_action.concept_name == "Recursion"

after = student.get_concept("Recursion")

assert after.mastery == mastery_before
assert after.attempts == attempts_before

print("PASS: Coding Agent selected:", result.recommended_action.action_type)
print("PASS: Recommended difficulty:", result.recommended_action.difficulty)
print("PASS: CACM mastery unchanged:", after.mastery)
print("PASS: Assessment attempts unchanged:", after.attempts)

unknown_coordinator = AgenticCodeReviewCoordinator(
    student=student,
    cognitive_engine=engine,
    reviewer=FakeReviewer("Unknown Programming Topic"),
)

unknown_result = unknown_coordinator.review_code("print('hello')")

assert unknown_result.practice_available is False
assert unknown_result.recommended_action is None

print("PASS: Unsupported concepts are handled safely")
print("ALL AGENTIC REVIEW TESTS PASSED")
