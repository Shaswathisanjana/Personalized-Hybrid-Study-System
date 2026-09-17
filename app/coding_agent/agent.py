from dataclasses import dataclass

from app.cognitive.models import StudentCognitiveModel


@dataclass
class CodingAction:
    """
    Decision produced by the Coding Agent.

    action_type:
        Type of coding activity the student should
        receive next.

    concept_name:
        Concept being assessed or practiced.

    difficulty:
        easy, medium, or hard.

    reason:
        Explanation for why the Coding Agent selected
        this action.
    """

    action_type: str
    concept_name: str
    difficulty: str
    reason: str


class CodingAgent:
    """
    Agent responsible for selecting the student's
    next coding activity.

    The Coding Agent does NOT maintain an independent
    learner model.

    Instead, it reads the shared StudentCognitiveModel
    maintained by CACM.

    Therefore, evidence collected by Learning,
    Research, or Coding can change the Coding Agent's
    future decision.
    """

    def choose_action(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
        has_active_conflict: bool = False,
    ) -> CodingAction:

        if not isinstance(
            student,
            StudentCognitiveModel,
        ):
            raise TypeError(
                "student must be a StudentCognitiveModel."
            )

        concept_name = concept_name.strip()

        if not concept_name:
            raise ValueError(
                "concept_name cannot be empty."
            )

        state = student.get_concept(
            concept_name
        )

        mastery = state.mastery
        confidence = state.confidence

        # ==================================================
        # 1. ACTIVE CROSS-AGENT CONFLICT
        # ==================================================
        #
        # If CACM detects disagreement between agents,
        # normal progression should temporarily stop.
        #
        # The Coding Agent requests a focused diagnostic
        # coding activity that can provide additional
        # evidence about the disputed concept.
        # ==================================================

        if has_active_conflict:

            return CodingAction(
                action_type="diagnostic_coding",
                concept_name=concept_name,
                difficulty="medium",
                reason=(
                    "Cross-agent cognitive evidence is "
                    "conflicting. Use a focused coding "
                    "activity to collect additional "
                    "evidence before normal progression."
                ),
            )

        # ==================================================
        # 2. LOW MASTERY
        # ==================================================

        if mastery < 0.40:

            return CodingAction(
                action_type="foundational_coding",
                concept_name=concept_name,
                difficulty="easy",
                reason=(
                    "Estimated mastery is low. Provide "
                    "a simple coding task that reinforces "
                    "the fundamental programming concept."
                ),
            )

        # ==================================================
        # 3. MODERATE MASTERY
        # ==================================================

        if mastery < 0.70:

            return CodingAction(
                action_type="guided_coding",
                concept_name=concept_name,
                difficulty="medium",
                reason=(
                    "Estimated mastery is moderate. "
                    "Provide a coding problem that "
                    "requires applying the concept with "
                    "moderate guidance."
                ),
            )

        # ==================================================
        # 4. HIGH MASTERY BUT LOW CONFIDENCE
        # ==================================================
        #
        # CACM currently thinks the student understands
        # the concept, but there is not yet enough
        # confidence in that estimate.
        #
        # Instead of immediately advancing, Coding
        # collects stronger verification evidence.
        # ==================================================

        if confidence < 0.50:

            return CodingAction(
                action_type="verification_coding",
                concept_name=concept_name,
                difficulty="hard",
                reason=(
                    "Estimated mastery is high, but "
                    "confidence in that estimate is low. "
                    "Use a harder coding task to verify "
                    "the student's understanding."
                ),
            )

        # ==================================================
        # 5. HIGH MASTERY + HIGH CONFIDENCE
        # ==================================================

        return CodingAction(
            action_type="advanced_coding",
            concept_name=concept_name,
            difficulty="hard",
            reason=(
                "Estimated mastery and confidence are "
                "high. Provide an advanced coding task "
                "that extends the student's understanding."
            ),
        )