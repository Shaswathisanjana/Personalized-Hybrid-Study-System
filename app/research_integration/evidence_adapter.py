from dataclasses import dataclass, field

from app.cognitive.evidence import LearningEvidence


@dataclass
class ResearchComprehensionResult:
    """
    Represents the result of a student's research-based
    comprehension activity.

    This is not yet cognitive evidence. The adapter below
    converts it into the common LearningEvidence format.
    """

    user_id: str
    concept_name: str

    # How well the student performed: 0.0 -> 1.0
    performance: float

    # Difficulty of the research activity: 0.0 -> 1.0
    difficulty: float

    # Confidence in this observation: 0.0 -> 1.0
    confidence: float

    activity_type: str = "research_comprehension"

    detected_misconceptions: list[str] = field(
        default_factory=list
    )


class ResearchEvidenceAdapter:
    """
    Converts a research comprehension result into the common
    LearningEvidence format understood by CognitiveEngine.

    Research Agent
          ↓
    ResearchComprehensionResult
          ↓
    ResearchEvidenceAdapter
          ↓
    LearningEvidence(source_agent="research")
          ↓
    CognitiveEngine
    """

    def to_learning_evidence(
        self,
        result: ResearchComprehensionResult,
    ) -> LearningEvidence:

        self._validate_result(result)

        # Initial heuristic:
        # higher-confidence research observations receive
        # slightly higher reliability.
        #
        # These values are NOT claimed to be scientifically
        # optimal. They will later be evaluated/calibrated.
        reliability = 0.50 + (0.30 * result.confidence)

        reliability = max(
            0.0,
            min(1.0, reliability),
        )

        return LearningEvidence(
            user_id=result.user_id,
            concept_name=result.concept_name,

            # Important: identifies this as Research Agent evidence.
            source_agent="research",

            evidence_type=result.activity_type,
            performance=result.performance,
            difficulty=result.difficulty,
            reliability=round(reliability, 3),

            detected_misconceptions=(
                result.detected_misconceptions
            ),
        )

    def _validate_result(
        self,
        result: ResearchComprehensionResult,
    ) -> None:

        if not result.user_id.strip():
            raise ValueError(
                "user_id cannot be empty."
            )

        if not result.concept_name.strip():
            raise ValueError(
                "concept_name cannot be empty."
            )

        self._validate_probability(
            "performance",
            result.performance,
        )

        self._validate_probability(
            "difficulty",
            result.difficulty,
        )

        self._validate_probability(
            "confidence",
            result.confidence,
        )

    @staticmethod
    def _validate_probability(
        name: str,
        value: float,
    ) -> None:

        if not 0.0 <= value <= 1.0:
            raise ValueError(
                f"{name} must be between 0 and 1."
            )
        