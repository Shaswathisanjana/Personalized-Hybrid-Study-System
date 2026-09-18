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

    The agent observes the student's shared cognitive
    state and autonomously decides what pedagogical
    action should be performed next.

    IMPORTANT:
    The agent does not generate educational content.
    It decides the pedagogical action.

    Content generation is handled separately by the
    configured ContentProvider.
    """

    def choose_action(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
        has_conflict: bool = False,
    ) -> LearningAction:

        # --------------------------------------------------
        # OBSERVE CURRENT COGNITIVE STATE
        # --------------------------------------------------

        concept = student.get_concept(concept_name)

        mastery = concept.mastery
        confidence = concept.confidence
        attempts = concept.attempts

        # --------------------------------------------------
        # RULE 1: CROSS-AGENT COGNITIVE CONFLICT
        # --------------------------------------------------
        #
        # Conflict has the highest priority because the
        # system should not confidently continue adapting
        # from contradictory evidence.
        # --------------------------------------------------

        if has_conflict:

            return LearningAction(
                action_type="diagnostic_quiz",
                concept_name=concept_name,
                difficulty="medium",
                reason=(
                    "Conflicting cognitive evidence exists "
                    "across agents. A diagnostic assessment "
                    "is required before normal progression."
                ),
            )

        # --------------------------------------------------
        # RULE 2: NO PERFORMANCE EVIDENCE YET
        # --------------------------------------------------
        #
        # A newly created concept may have a neutral prior
        # mastery value, but that does NOT mean the student
        # has demonstrated moderate understanding.
        #
        # attempts == 0 means CACM has not yet received
        # performance evidence for this concept.
        #
        # Therefore, begin with teaching rather than
        # assuming the student is ready for practice.
        # --------------------------------------------------

        if attempts == 0:

            return LearningAction(
                action_type="teach_concept",
                concept_name=concept_name,
                difficulty="easy",
                reason=(
                    "No performance evidence is available "
                    "for this concept yet. The current mastery "
                    "value is only an initial estimate, so the "
                    "student should first receive foundational "
                    "instruction."
                ),
            )

        # --------------------------------------------------
        # RULE 3: LOW MASTERY
        # --------------------------------------------------

        if mastery < 0.40:

            return LearningAction(
                action_type="teach_concept",
                concept_name=concept_name,
                difficulty="easy",
                reason=(
                    "Observed performance indicates low "
                    "mastery, so the concept should be "
                    "explained or remediated before further "
                    "assessment."
                ),
            )

        # --------------------------------------------------
        # RULE 4: MODERATE MASTERY
        # --------------------------------------------------

        if mastery < 0.70:

            return LearningAction(
                action_type="practice_quiz",
                concept_name=concept_name,
                difficulty="medium",
                reason=(
                    "The student has demonstrated partial "
                    "understanding. Additional practice is "
                    "needed to strengthen mastery."
                ),
            )

        # --------------------------------------------------
        # RULE 5: HIGH MASTERY BUT LOW CONFIDENCE
        # --------------------------------------------------
        #
        # The current estimate is high, but CACM does not
        # yet have enough confidence in that estimate.
        # --------------------------------------------------

        if confidence < 0.50:

            return LearningAction(
                action_type="verification_quiz",
                concept_name=concept_name,
                difficulty="hard",
                reason=(
                    "Estimated mastery is high, but confidence "
                    "in the estimate is still low. Independent "
                    "verification is required."
                ),
            )

        # --------------------------------------------------
        # RULE 6: HIGH MASTERY + SUFFICIENT CONFIDENCE
        # --------------------------------------------------

        return LearningAction(
            action_type="advance_topic",
            concept_name=concept_name,
            difficulty="hard",
            reason=(
                "The student has demonstrated high mastery "
                "with sufficient confidence, so progression "
                "to advanced material is appropriate."
            ),
        )