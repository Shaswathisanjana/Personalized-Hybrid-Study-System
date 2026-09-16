from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ConceptState:
    """
    Represents the student's knowledge state
    for one concept.
    """

    concept_name: str

    # 0.0 = no mastery, 1.0 = complete mastery
    mastery: float = 0.5

    # How confident we are in the mastery estimate
    confidence: float = 0.0

    # Number of interactions observed
    attempts: int = 0

    # Misconceptions detected for this concept
    misconceptions: list[str] = field(default_factory=list)

    # Time of most recent update
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class StudentCognitiveModel:
    """
    Represents the complete cognitive profile
    of one student.
    """

    user_id: str

    # Stores every concept and its cognitive state
    concepts: dict[str, ConceptState] = field(default_factory=dict)

    def get_concept(self, concept_name: str) -> ConceptState:
        """
        Get a concept from the student's profile.

        If it does not exist yet, create it automatically.
        """

        if concept_name not in self.concepts:
            self.concepts[concept_name] = ConceptState(
                concept_name=concept_name
            )

        return self.concepts[concept_name]