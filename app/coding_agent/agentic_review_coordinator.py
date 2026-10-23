from app.cognitive.concept_identity import concept_id
from dataclasses import dataclass

from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine

from app.coding_agent.agent import CodingAgent, CodingAction
from app.coding_agent.ai_code_reviewer import (
    AICodeReviewer,
    AIReviewResult,
)



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

        if not concept_name.strip():
            return ""
        # Only exact, shared identities can select a verified practice topic.
        # Python Lists and factorial are not synonyms for Arrays/Recursion.
        from app.coding_agent.verified_exercises import VERIFIED_CONCEPTS
        return next((name for name in VERIFIED_CONCEPTS if concept_id(name) == concept_id(concept_name)), "")

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
