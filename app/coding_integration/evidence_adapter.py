from dataclasses import dataclass

from app.cognitive.evidence import LearningEvidence
from app.coding_agent.models import CodingEvaluation


@dataclass
class CodingPerformanceResult:
    """
    Normalized result produced from a Coding Agent
    evaluation before it enters CACM.

    performance:
        Estimated demonstrated understanding of the
        target concept.

    confidence:
        Confidence in the Coding Agent's evaluation,
        NOT the student's confidence.
    """

    user_id: str
    concept_name: str

    performance: float
    difficulty: float
    confidence: float

    activity_type: str = "coding_task"

    detected_misconceptions: list[str] = None

    def __post_init__(self):
        self.user_id = self.user_id.strip()
        self.concept_name = self.concept_name.strip()

        if not self.user_id:
            raise ValueError(
                "user_id cannot be empty."
            )

        if not self.concept_name:
            raise ValueError(
                "concept_name cannot be empty."
            )

        if not 0.0 <= self.performance <= 1.0:
            raise ValueError(
                "performance must be between 0 and 1."
            )

        if not 0.0 <= self.difficulty <= 1.0:
            raise ValueError(
                "difficulty must be between 0 and 1."
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "confidence must be between 0 and 1."
            )

        if self.detected_misconceptions is None:
            self.detected_misconceptions = []


class CodingEvidenceAdapter:
    """
    Converts Coding Agent evaluation results into
    CACM-compatible LearningEvidence.

    This adapter is the bridge:

        Coding Agent
             ↓
        CodingPerformanceResult
             ↓
        LearningEvidence(source_agent="coding")
             ↓
        CognitiveEngine
    """

    def from_evaluation(
        self,
        user_id: str,
        concept_name: str,
        difficulty: float,
        evaluation: CodingEvaluation,
    ) -> CodingPerformanceResult:

        if not isinstance(
            evaluation,
            CodingEvaluation,
        ):
            raise TypeError(
                "evaluation must be a CodingEvaluation."
            )

        return CodingPerformanceResult(
            user_id=user_id,
            concept_name=concept_name,
            performance=evaluation.performance,
            difficulty=difficulty,
            confidence=evaluation.confidence,
            detected_misconceptions=list(
                evaluation.detected_misconceptions
            ),
        )

    def to_learning_evidence(
        self,
        result: CodingPerformanceResult,
    ) -> LearningEvidence:
        """
        Convert normalized coding performance into
        the common cognitive evidence representation.
        """

        if not isinstance(
            result,
            CodingPerformanceResult,
        ):
            raise TypeError(
                "result must be a CodingPerformanceResult."
            )

        # --------------------------------------------------
        # Evidence reliability
        # --------------------------------------------------
        #
        # Coding evidence has two useful characteristics:
        #
        # 1. Behavioral tests provide objective evidence.
        # 2. Semantic evaluation provides interpretation.
        #
        # We therefore map evaluator confidence into a
        # moderate-to-high reliability range.
        #
        # IMPORTANT:
        # This mapping is currently a heuristic and should
        # later be calibrated experimentally.
        # --------------------------------------------------

        reliability = (
            0.60
            +
            0.30 * result.confidence
        )

        reliability = max(
            0.0,
            min(
                1.0,
                reliability,
            ),
        )

        return LearningEvidence(
            user_id=result.user_id,
            concept_name=result.concept_name,
            source_agent="coding",
            evidence_type=result.activity_type,
            performance=result.performance,
            difficulty=result.difficulty,
            reliability=reliability,
            detected_misconceptions=list(
                result.detected_misconceptions
            ),
        )