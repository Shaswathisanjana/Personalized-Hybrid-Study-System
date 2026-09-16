from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class LearningEvidence:
    """
    A standard evidence format used by all agents.

    Learning Agent, Research Agent and Coding Agent
    will convert their observations into this format
    before sending them to the cognitive engine.
    """

    # Student who generated the evidence
    user_id: str

    # Concept being evaluated
    # Example: Recursion, SQL Joins, Neural Networks
    concept_name: str

    # Agent that generated the evidence
    # learning / research / coding
    source_agent: str

    # Activity that generated the evidence
    # quiz / coding_solution / research_question etc.
    evidence_type: str

    # Student performance: 0.0 to 1.0
    performance: float

    # Task difficulty: 0.0 to 1.0
    difficulty: float

    # Strength/reliability of the evidence: 0.0 to 1.0
    reliability: float

    # Automatically record when evidence was generated
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """
        Validate and normalize the evidence after creation.
        """

        # Remove unnecessary spaces
        self.user_id = self.user_id.strip()
        self.concept_name = self.concept_name.strip()

        # Store these consistently in lowercase
        self.source_agent = self.source_agent.strip().lower()
        self.evidence_type = self.evidence_type.strip().lower()

        # Required fields cannot be empty
        if not self.user_id:
            raise ValueError("user_id cannot be empty.")

        if not self.concept_name:
            raise ValueError("concept_name cannot be empty.")

        # Only our current agents are accepted
        valid_agents = {
            "learning",
            "research",
            "coding"
        }

        if self.source_agent not in valid_agents:
            raise ValueError(
                f"source_agent must be one of {valid_agents}."
            )

        # Numeric values must stay between 0 and 1
        if not 0.0 <= self.performance <= 1.0:
            raise ValueError(
                "performance must be between 0.0 and 1.0."
            )

        if not 0.0 <= self.difficulty <= 1.0:
            raise ValueError(
                "difficulty must be between 0.0 and 1.0."
            )

        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError(
                "reliability must be between 0.0 and 1.0."
            )