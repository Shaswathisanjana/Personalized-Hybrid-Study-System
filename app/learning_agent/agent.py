from dataclasses import dataclass

from app.cognitive.models import StudentCognitiveModel


@dataclass
class LearningAction:
    """
    Represents an action selected by the Learning Agent.
    """

    action_type: str
    concept_name: str
    difficulty: str
    reason: str


class LearningAgent:
    """
    Personalized Learning Agent.

    The agent observes the student's cognitive state
    and autonomously decides what learning action
    should be performed next.
    """

    def choose_action(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
        has_conflict: bool = False,
    ) -> LearningAction:

        # Get current knowledge state.
        concept = student.get_concept(concept_name)

        mastery = concept.mastery
        confidence = concept.confidence

        # --------------------------------------------------
        # RULE 1: Cognitive conflict exists
        # --------------------------------------------------

        if has_conflict:

            return LearningAction(
                action_type="diagnostic_quiz",
                concept_name=concept_name,
                difficulty="medium",
                reason=(
                    "Conflicting evidence exists across agents. "
                    "A diagnostic assessment is required."
                ),
            )

        # --------------------------------------------------
        # RULE 2: Low mastery
        # --------------------------------------------------

        if mastery < 0.40:

            return LearningAction(
                action_type="teach_concept",
                concept_name=concept_name,
                difficulty="easy",
                reason=(
                    "Mastery is low, so the concept should "
                    "be explained before further assessment."
                ),
            )

        # --------------------------------------------------
        # RULE 3: Moderate mastery
        # --------------------------------------------------

        if mastery < 0.70:

            return LearningAction(
                action_type="practice_quiz",
                concept_name=concept_name,
                difficulty="medium",
                reason=(
                    "Mastery is moderate. Practice is needed "
                    "to strengthen understanding."
                ),
            )

        # --------------------------------------------------
        # RULE 4: High mastery but low confidence
        # --------------------------------------------------

        if confidence < 0.50:

            return LearningAction(
                action_type="verification_quiz",
                concept_name=concept_name,
                difficulty="hard",
                reason=(
                    "Estimated mastery is high, but confidence "
                    "in that estimate is still low."
                ),
            )

        # --------------------------------------------------
        # RULE 5: High mastery and sufficient confidence
        # --------------------------------------------------

        return LearningAction(
            action_type="advance_topic",
            concept_name=concept_name,
            difficulty="hard",
            reason=(
                "Mastery and confidence are sufficiently high "
                "to progress to more advanced material."
            ),
        )