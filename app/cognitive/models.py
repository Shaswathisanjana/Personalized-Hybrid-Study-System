from app.cognitive.concept_identity import concept_id
from dataclasses import dataclass, field
from datetime import datetime

from app.cognitive.misconception_tracker import (
    MisconceptionHypothesis,
)


@dataclass
class ConceptState:
    """
    Stores the cognitive state of a student
    for one concept.
    """

    concept_name: str

    mastery: float = 0.5
    confidence: float = 0.0
    attempts: int = 0

    # --------------------------------------------------
    # LEGACY / COMPATIBILITY FIELD
    # --------------------------------------------------
    # Existing parts of our project currently use
    # a simple list of misconception descriptions.
    #
    # We keep this temporarily so that our older
    # pipeline continues to work.
    # --------------------------------------------------

    misconceptions: list[str] = field(
        default_factory=list
    )

    # --------------------------------------------------
    # NEW STRUCTURED MISCONCEPTION MODEL
    # --------------------------------------------------
    # Each misconception can now have:
    #
    # confidence
    # supporting evidence
    # contradicting evidence
    # status
    # source agents
    #
    # Key   -> misconception description
    # Value -> MisconceptionHypothesis
    # --------------------------------------------------

    misconception_hypotheses: dict[
        str,
        MisconceptionHypothesis
    ] = field(
        default_factory=dict
    )

    last_updated: datetime = field(
        default_factory=datetime.now
    )


    def get_active_misconceptions(
        self,
    ) -> list[MisconceptionHypothesis]:
        """
        Returns misconceptions that are currently
        considered active.
        """

        return [
            hypothesis
            for hypothesis
            in self.misconception_hypotheses.values()
            if hypothesis.status == "active"
        ]


    def get_uncertain_misconceptions(
        self,
    ) -> list[MisconceptionHypothesis]:
        """
        Returns hypotheses for which the evidence
        is currently uncertain.
        """

        return [
            hypothesis
            for hypothesis
            in self.misconception_hypotheses.values()
            if hypothesis.status == "uncertain"
        ]


    def get_resolved_misconceptions(
        self,
    ) -> list[MisconceptionHypothesis]:
        """
        Returns misconceptions that currently have
        enough contradicting evidence to be treated
        as resolved.
        """

        return [
            hypothesis
            for hypothesis
            in self.misconception_hypotheses.values()
            if hypothesis.status == "resolved"
        ]


@dataclass
class StudentCognitiveModel:
    """
    Shared cognitive model for one student.

    Learning, Research and Coding agents will
    eventually read and update this same state.
    """

    user_id: str

    concepts: dict[
        str,
        ConceptState
    ] = field(
        default_factory=dict
    )


    def get_concept(
        self,
        concept_name: str,
    ) -> ConceptState:
        """
        Returns the student's state for a concept.

        If the concept has never been observed,
        a new ConceptState is automatically created.
        """

        from app.cognitive.concept_identity import clean_concept_name
        concept_name = clean_concept_name(concept_name)
        existing = self.find_concept(concept_name)
        if existing is not None:
            return existing
        state = ConceptState(concept_name=concept_name)
        self.concepts[concept_name] = state
        return state

    def find_concept(self, concept_name: str) -> ConceptState | None:
        """Read an existing identity without creating a neutral prior."""
        identity = concept_id(concept_name)
        matches = [state for name, state in self.concepts.items()
                   if concept_id(name) == identity]
        if len(matches) > 1:
            raise ValueError("Duplicate concept identities require the saved-state migration.")
        return matches[0] if matches else None
