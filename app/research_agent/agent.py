from dataclasses import dataclass

from app.cognitive.models import StudentCognitiveModel


@dataclass
class ResearchAction:
    """
    Represents the next research-oriented learning action
    selected for a student.
    """

    action_type: str
    concept_name: str
    difficulty: str
    reason: str


class ResearchAgent:
    """
    Research Agent decision layer.

    The Research Agent reads the shared CACM
    StudentCognitiveModel and selects an appropriate
    research-oriented learning activity.

    This allows cognitive evidence produced by other
    agents to influence Research Agent behaviour.
    """

    def choose_action(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
        has_active_conflict: bool = False,
    ) -> ResearchAction:

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

        # --------------------------------------------------
        # 1. CROSS-AGENT CONFLICT
        #
        # If CACM reports contradictory evidence,
        # Research Agent should not simply continue
        # normal content progression.
        # --------------------------------------------------

        if has_active_conflict:

            return ResearchAction(
                action_type="diagnostic_research",
                concept_name=concept_name,
                difficulty="medium",
                reason=(
                    "Cross-agent evidence is conflicting. "
                    "Use a focused research activity to "
                    "collect additional evidence before "
                    "normal progression."
                ),
            )

        # --------------------------------------------------
        # 2. LOW MASTERY
        #
        # Student needs simpler explanatory material.
        # --------------------------------------------------

        if mastery < 0.40:

            return ResearchAction(
                action_type="foundational_research",
                concept_name=concept_name,
                difficulty="easy",
                reason=(
                    "Estimated mastery is low. "
                    "Provide foundational research material "
                    "with simple explanations and examples."
                ),
            )

        # --------------------------------------------------
        # 3. MODERATE MASTERY
        #
        # Student understands some of the concept but
        # still benefits from guided research.
        # --------------------------------------------------

        if mastery < 0.70:

            return ResearchAction(
                action_type="guided_research",
                concept_name=concept_name,
                difficulty="medium",
                reason=(
                    "Estimated mastery is moderate. "
                    "Provide guided research material that "
                    "deepens conceptual understanding."
                ),
            )

        # --------------------------------------------------
        # 4. HIGH MASTERY BUT LOW CONFIDENCE
        #
        # CACM thinks mastery is high, but the estimate
        # is not yet sufficiently reliable.
        # --------------------------------------------------

        if confidence < 0.50:

            return ResearchAction(
                action_type="verification_research",
                concept_name=concept_name,
                difficulty="hard",
                reason=(
                    "Estimated mastery is high, but "
                    "confidence in that estimate is low. "
                    "Use research comprehension to verify "
                    "the student's understanding."
                ),
            )

        # --------------------------------------------------
        # 5. HIGH MASTERY + HIGH CONFIDENCE
        #
        # Student is ready for deeper research material.
        # --------------------------------------------------

        return ResearchAction(
            action_type="advanced_research",
            concept_name=concept_name,
            difficulty="hard",
            reason=(
                "Estimated mastery and confidence are high. "
                "Provide advanced research material that "
                "extends the student's understanding."
            ),
        )
    