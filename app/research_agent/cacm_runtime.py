from __future__ import annotations

from dataclasses import dataclass

from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.models import StudentCognitiveModel

from app.research_agent.models import (
    ResearchComprehensionEvaluation,
    ResearchComprehensionQuestion,
)

from app.research_integration.evidence_adapter import (
    ResearchComprehensionResult,
    ResearchEvidenceAdapter,
)


@dataclass
class ResearchCACMOutcome:
    """
    Result produced after a Research Agent comprehension
    evaluation is sent into the shared CACM cognitive model.
    """

    concept_name: str
    performance: float
    confidence: float
    cognitive_result: dict
    has_active_conflict: bool


class ResearchCACMRuntime:
    """
    Connects the Research Agent to CACM.

    Flow:

    Research comprehension evaluation
                ↓
    ResearchComprehensionResult
                ↓
    ResearchEvidenceAdapter
                ↓
    LearningEvidence(source_agent="research")
                ↓
    CognitiveEngine
                ↓
    Shared StudentCognitiveModel
    """

    # Current heuristic mapping between textual
    # question difficulty and CACM numeric difficulty.
    DIFFICULTY_MAP = {
        "easy": 0.30,
        "medium": 0.60,
        "hard": 0.90,
    }

    def __init__(
        self,
        cognitive_engine: CognitiveEngine,
        student: StudentCognitiveModel,
        evidence_adapter: ResearchEvidenceAdapter | None = None,
    ):
        """
        The Research Agent receives the SAME student model
        that is used by the other educational agents.
        """

        self.cognitive_engine = cognitive_engine
        self.student = student

        self.evidence_adapter = (
            evidence_adapter
            if evidence_adapter is not None
            else ResearchEvidenceAdapter()
        )

    def process_comprehension(
        self,
        user_id: str,
        question: ResearchComprehensionQuestion,
        evaluation: ResearchComprehensionEvaluation,
    ) -> ResearchCACMOutcome:
        """
        Process a student's Research Agent comprehension
        performance through CACM.
        """

        # --------------------------------------------------
        # 1. Validate user
        # --------------------------------------------------

        user_id = user_id.strip()

        if not user_id:
            raise ValueError(
                "User ID cannot be empty."
            )

        # The evidence must belong to the same student
        # represented by the shared cognitive model.
        if user_id != self.student.user_id:
            raise ValueError(
                "Research result user_id does not match "
                "the shared StudentCognitiveModel user_id."
            )

        # --------------------------------------------------
        # 2. Validate concept
        # --------------------------------------------------

        concept_name = (
            question.concept_name.strip()
        )

        if not concept_name:
            raise ValueError(
                "Concept name cannot be empty."
            )

        # --------------------------------------------------
        # 3. Convert question difficulty
        # --------------------------------------------------

        difficulty = (
            self._difficulty_to_numeric(
                question.difficulty
            )
        )

        # --------------------------------------------------
        # 4. Build Research Agent comprehension result
        #
        # This is still Research Agent information.
        # --------------------------------------------------

        research_result = (
            ResearchComprehensionResult(
                user_id=user_id,
                concept_name=concept_name,
                performance=evaluation.performance,
                difficulty=difficulty,
                confidence=evaluation.confidence,
                activity_type="research_comprehension",
                detected_misconceptions=list(
                    evaluation.detected_misconceptions
                ),
            )
        )

        # --------------------------------------------------
        # 5. Convert Research result into CACM evidence
        #
        # IMPORTANT:
        #
        # The existing ResearchEvidenceAdapter method is:
        #
        #       to_learning_evidence()
        #
        # Even though the object type is LearningEvidence,
        # the source_agent inside it is "research".
        #
        # Therefore CACM still knows this evidence came
        # from the Research Agent.
        # --------------------------------------------------

        cognitive_evidence = (
            self.evidence_adapter.to_learning_evidence(
                research_result
            )
        )

        # --------------------------------------------------
        # 6. Send evidence into CACM
        #
        # process_evidence requires:
        #
        #   StudentCognitiveModel
        #   LearningEvidence
        #
        # We pass the SAME shared student object that the
        # Learning Agent used.
        # --------------------------------------------------

        cognitive_result = (
            self.cognitive_engine.process_evidence(
                self.student,
                cognitive_evidence,
            )
        )

        # --------------------------------------------------
        # 7. Return integration result
        # --------------------------------------------------

        return ResearchCACMOutcome(
            concept_name=concept_name,
            performance=evaluation.performance,
            confidence=evaluation.confidence,
            cognitive_result=cognitive_result,
            has_active_conflict=bool(
                cognitive_result.get(
                    "has_active_conflict",
                    False,
                )
            ),
        )

    @classmethod
    def _difficulty_to_numeric(
        cls,
        difficulty: str,
    ) -> float:
        """
        Convert:
            easy   -> 0.30
            medium -> 0.60
            hard   -> 0.90

        These values are project heuristics and can later
        be calibrated experimentally.
        """

        normalized = (
            difficulty.strip().lower()
        )

        if normalized not in cls.DIFFICULTY_MAP:
            raise ValueError(
                "Research question difficulty must be "
                "'easy', 'medium', or 'hard'."
            )

        return cls.DIFFICULTY_MAP[
            normalized
        ]