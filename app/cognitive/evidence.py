from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class LearningEvidence:
    user_id: str
    concept_name: str
    source_agent: str
    evidence_type: str

    performance: float
    difficulty: float
    reliability: float

    # Misconceptions supported by this specific
    # piece of evidence.
    detected_misconceptions: list[str] = field(
        default_factory=list
    )

    timestamp: datetime = field(
        default_factory=datetime.now
    )

    def __post_init__(self):

        self.user_id = self.user_id.strip()
        self.concept_name = self.concept_name.strip()

        self.source_agent = (
            self.source_agent
            .strip()
            .lower()
        )

        self.evidence_type = (
            self.evidence_type
            .strip()
            .lower()
        )

        if not self.user_id:
            raise ValueError(
                "user_id cannot be empty."
            )

        if not self.concept_name:
            raise ValueError(
                "concept_name cannot be empty."
            )

        valid_agents = {
            "learning",
            "research",
            "coding",
        }

        if self.source_agent not in valid_agents:
            raise ValueError(
                f"source_agent must be one of "
                f"{valid_agents}."
            )

        if not 0.0 <= self.performance <= 1.0:
            raise ValueError(
                "performance must be between "
                "0.0 and 1.0."
            )

        if not 0.0 <= self.difficulty <= 1.0:
            raise ValueError(
                "difficulty must be between "
                "0.0 and 1.0."
            )

        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError(
                "reliability must be between "
                "0.0 and 1.0."
            )

        # Remove empty strings and duplicates.
        self.detected_misconceptions = list(
            dict.fromkeys(
                misconception.strip()
                for misconception
                in self.detected_misconceptions
                if misconception.strip()
            )
        )