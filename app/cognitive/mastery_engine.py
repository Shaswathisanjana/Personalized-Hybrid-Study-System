from datetime import datetime

from app.cognitive.models import StudentCognitiveModel


class MasteryEngine:
    """
    Updates a student's concept mastery whenever
    new learning evidence is received.
    """

    def update_mastery(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
        observed_performance: float,
        evidence_reliability: float,
    ):
        # Get the student's current state for this concept.
        concept = student.get_concept(concept_name)

        # Store the old mastery before updating it.
        old_mastery = concept.mastery

        # Update mastery using the new evidence.
        new_mastery = old_mastery + (
            evidence_reliability
            * (observed_performance - old_mastery)
        )

        # Mastery must always stay between 0 and 1.
        new_mastery = max(0.0, min(1.0, new_mastery))

        # Save the updated mastery.
        concept.mastery = round(new_mastery, 3)

        # One more learning interaction has occurred.
        concept.attempts += 1

        # More evidence means we become more confident
        # about our estimate of the student's knowledge.
        concept.confidence = min(
            1.0,
            concept.confidence + (0.1 * evidence_reliability)
        )

        concept.confidence = round(concept.confidence, 3)

        # Remember when this concept was last updated.
        concept.last_updated = datetime.now()

        return concept