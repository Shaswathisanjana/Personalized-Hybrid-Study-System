from dataclasses import dataclass

from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.models import StudentCognitiveModel

from app.coding_agent.models import CodingEvaluation

from app.coding_integration.evidence_adapter import (
    CodingEvidenceAdapter,
)


@dataclass
class CodingCACMOutcome:
    """
    Result produced after Coding Agent evidence
    has been submitted to CACM.
    """

    concept_name: str
    performance: float
    confidence: float

    cognitive_result: dict

    has_active_conflict: bool


class CodingCACMRuntime:
    """
    Bridge between the Coding Agent and CACM.

    Flow:

        CodingEvaluation
              ↓
        CodingEvidenceAdapter
              ↓
        LearningEvidence(
            source_agent="coding"
        )
              ↓
        CognitiveEngine
              ↓
        Shared StudentCognitiveModel
    """

    DIFFICULTY_MAP = {
        "easy": 0.30,
        "medium": 0.60,
        "hard": 0.90,
    }

    def __init__(
        self,
        cognitive_engine: CognitiveEngine,
        student: StudentCognitiveModel,
        evidence_adapter=None,
    ):
        if not isinstance(
            cognitive_engine,
            CognitiveEngine,
        ):
            raise TypeError(
                "cognitive_engine must be a CognitiveEngine."
            )

        if not isinstance(
            student,
            StudentCognitiveModel,
        ):
            raise TypeError(
                "student must be a StudentCognitiveModel."
            )

        self.cognitive_engine = cognitive_engine
        self.student = student

        self.evidence_adapter = (
            evidence_adapter
            or CodingEvidenceAdapter()
        )

    def submit_evaluation(
        self,
        user_id: str,
        concept_name: str,
        difficulty: str,
        evaluation: CodingEvaluation,
    ) -> CodingCACMOutcome:
        """
        Submit Coding Agent evaluation evidence
        to the shared cognitive model.
        """

        user_id = user_id.strip()
        concept_name = concept_name.strip()
        difficulty = difficulty.strip().lower()

        if not user_id:
            raise ValueError(
                "user_id cannot be empty."
            )

        if not concept_name:
            raise ValueError(
                "concept_name cannot be empty."
            )

        # --------------------------------------------------
        # Make sure the evidence belongs to the same
        # student represented by this shared model.
        # --------------------------------------------------

        if user_id != self.student.user_id:
            raise ValueError(
                "Coding evidence user_id does not match "
                "the shared StudentCognitiveModel."
            )

        if difficulty not in self.DIFFICULTY_MAP:
            raise ValueError(
                "difficulty must be easy, medium, or hard."
            )

        if not isinstance(
            evaluation,
            CodingEvaluation,
        ):
            raise TypeError(
                "evaluation must be a CodingEvaluation."
            )

        numeric_difficulty = (
            self.DIFFICULTY_MAP[
                difficulty
            ]
        )

        # --------------------------------------------------
        # 1. Convert CodingEvaluation into the normalized
        #    CodingPerformanceResult.
        # --------------------------------------------------

        coding_result = (
            self.evidence_adapter.from_evaluation(
                user_id=user_id,
                concept_name=concept_name,
                difficulty=numeric_difficulty,
                evaluation=evaluation,
            )
        )

        # --------------------------------------------------
        # 2. Convert it into CACM's common evidence format.
        # --------------------------------------------------

        evidence = (
            self.evidence_adapter.to_learning_evidence(
                coding_result
            )
        )

        # --------------------------------------------------
        # 3. Submit evidence to the existing CognitiveEngine.
        #
        # This can:
        # - update mastery
        # - update confidence
        # - update misconception hypotheses
        # - detect cross-agent conflicts
        # --------------------------------------------------

        cognitive_result = (
            self.cognitive_engine.process_evidence(
                self.student,
                evidence,
            )
        )

        # --------------------------------------------------
        # 4. Check whether CACM now has an unresolved
        #    conflict for this concept.
        # --------------------------------------------------

        has_active_conflict = (
            self.cognitive_engine.has_conflict(
                user_id,
                concept_name,
            )
        )

        return CodingCACMOutcome(
            concept_name=concept_name,
            performance=evaluation.performance,
            confidence=evaluation.confidence,
            cognitive_result=cognitive_result,
            has_active_conflict=has_active_conflict,
        )