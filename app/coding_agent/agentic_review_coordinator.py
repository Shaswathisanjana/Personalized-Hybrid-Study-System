from dataclasses import dataclass

from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine

from app.coding_agent.agent import CodingAgent, CodingAction
from app.coding_agent.ai_code_reviewer import (
    AICodeReviewer,
    AIReviewResult,
)


SUPPORTED_CONCEPTS = {
    "recursion": "Recursion",
    "recursive": "Recursion",
    "factorial": "Recursion",
    "prime": "Prime Numbers",
    "prime number": "Prime Numbers",
    "prime numbers": "Prime Numbers",
    "array": "Arrays",
    "arrays": "Arrays",
    "list": "Arrays",
    "lists": "Arrays",
}


@dataclass
class AgenticReviewOutcome:
    review: AIReviewResult
    identified_concept: str
    recommended_action: CodingAction | None
    practice_available: bool
    decision_reason: str


class AgenticCodeReviewCoordinator:
    """
    Connects AI code review with the existing Coding Agent
    and shared CACM cognitive state.

    Reviewing code alone does NOT submit learning evidence
    or modify student mastery.
    """

    def __init__(
        self,
        student: StudentCognitiveModel,
        cognitive_engine: CognitiveEngine,
        reviewer=None,
        coding_agent=None,
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

        self.reviewer = reviewer
        self.coding_agent = coding_agent or CodingAgent()

    @staticmethod
    def normalize_concept(concept_name: str) -> str:
        if not isinstance(concept_name, str):
            return ""

        normalized = " ".join(
            concept_name.strip().lower().replace("_", " ").split()
        )

        # First try an exact supported-concept match.
        exact_match = SUPPORTED_CONCEPTS.get(normalized, "")
        if exact_match:
            return exact_match

        # Gemini often returns descriptive learning-concept names.
        # Map clear variants to our existing verified practice topics.
        words = set(normalized.replace("-", " ").split())

        if (
            "recursion" in words
            or "recursive" in words
            or "factorial" in words
        ):
            return "Recursion"

        if "prime" in words:
            return "Prime Numbers"

        if "array" in words or "arrays" in words:
            return "Arrays"

        return ""

    def review_code(self, code: str) -> AgenticReviewOutcome:
        if not isinstance(code, str) or not code.strip():
            raise ValueError(
                "Please paste Python code before requesting a review."
            )

        if self.reviewer is None:
            self.reviewer = AICodeReviewer()

        review = self.reviewer.review(code)

        concept = self.normalize_concept(
            review.learning_concept
        )

        if not concept:
            return AgenticReviewOutcome(
                review=review,
                identified_concept=review.learning_concept,
                recommended_action=None,
                practice_available=False,
                decision_reason=(
                    "The reviewer identified a concept that is not "
                    "yet mapped to our verified practice bank. "
                    "No unsupported practice recommendation "
                    "has been generated."
                ),
            )

        # Read the genuine conflict state from the shared engine.
        has_conflict = self.cognitive_engine.has_conflict(
            user_id=self.student.user_id,
            concept_name=concept,
        )

        # Reuse the existing Coding Agent's decision policy.
        action = self.coding_agent.choose_action(
            student=self.student,
            concept_name=concept,
            has_active_conflict=has_conflict,
        )

        return AgenticReviewOutcome(
            review=review,
            identified_concept=concept,
            recommended_action=action,
            practice_available=True,
            decision_reason=(
                "The Coding Agent selected this intervention "
                "using the student's shared CACM cognitive state "
                "and current conflict status."
            ),
        )
