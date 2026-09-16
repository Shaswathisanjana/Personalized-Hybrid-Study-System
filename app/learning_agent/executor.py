from dataclasses import dataclass

from app.learning_agent.agent import LearningAction


@dataclass
class LearningActivity:
    """
    Represents the actual learning activity produced
    after the Learning Agent selects an action.
    """

    activity_type: str
    concept_name: str
    difficulty: str
    content: str
    requires_response: bool


class LearningActionExecutor:
    """
    Executes decisions made by the Learning Agent.

    The LearningAgent decides WHAT should happen.
    The LearningActionExecutor decides HOW that
    learning action is presented to the student.

    For now, activities are generated using local
    templates. Later, an LLM/content provider can
    replace these templates without changing the
    cognitive decision system.
    """

    def execute(
        self,
        action: LearningAction,
    ) -> LearningActivity:

        if action.action_type == "teach_concept":
            return self._teach_concept(action)

        if action.action_type == "practice_quiz":
            return self._practice_quiz(action)

        if action.action_type == "diagnostic_quiz":
            return self._diagnostic_quiz(action)

        if action.action_type == "verification_quiz":
            return self._verification_quiz(action)

        if action.action_type == "advance_topic":
            return self._advance_topic(action)

        raise ValueError(
            f"Unknown learning action: {action.action_type}"
        )


    # ==================================================
    # TEACH CONCEPT
    # ==================================================

    def _teach_concept(
        self,
        action: LearningAction,
    ) -> LearningActivity:

        content = (
            f"Let's strengthen your understanding of "
            f"{action.concept_name}. "
            f"We will begin with a simple explanation "
            f"and then check your understanding."
        )

        return LearningActivity(
            activity_type="lesson",
            concept_name=action.concept_name,
            difficulty=action.difficulty,
            content=content,
            requires_response=False,
        )


    # ==================================================
    # PRACTICE QUIZ
    # ==================================================

    def _practice_quiz(
        self,
        action: LearningAction,
    ) -> LearningActivity:

        content = (
            f"Practice question for {action.concept_name}: "
            f"Apply the concept to solve a "
            f"{action.difficulty}-difficulty question."
        )

        return LearningActivity(
            activity_type="practice_quiz",
            concept_name=action.concept_name,
            difficulty=action.difficulty,
            content=content,
            requires_response=True,
        )


    # ==================================================
    # DIAGNOSTIC QUIZ
    # ==================================================

    def _diagnostic_quiz(
        self,
        action: LearningAction,
    ) -> LearningActivity:

        content = (
            f"Diagnostic assessment for "
            f"{action.concept_name}: "
            f"This assessment is being used because "
            f"different learning signals disagree about "
            f"your current understanding."
        )

        return LearningActivity(
            activity_type="diagnostic_quiz",
            concept_name=action.concept_name,
            difficulty=action.difficulty,
            content=content,
            requires_response=True,
        )


    # ==================================================
    # VERIFICATION QUIZ
    # ==================================================

    def _verification_quiz(
        self,
        action: LearningAction,
    ) -> LearningActivity:

        content = (
            f"Verification question for "
            f"{action.concept_name}: "
            f"Your estimated mastery is high, but "
            f"additional evidence is needed before "
            f"progressing."
        )

        return LearningActivity(
            activity_type="verification_quiz",
            concept_name=action.concept_name,
            difficulty=action.difficulty,
            content=content,
            requires_response=True,
        )


    # ==================================================
    # ADVANCE TOPIC
    # ==================================================

    def _advance_topic(
        self,
        action: LearningAction,
    ) -> LearningActivity:

        content = (
            f"You have demonstrated sufficient evidence "
            f"of understanding {action.concept_name}. "
            f"The system can now move toward a more "
            f"advanced related topic."
        )

        return LearningActivity(
            activity_type="topic_progression",
            concept_name=action.concept_name,
            difficulty=action.difficulty,
            content=content,
            requires_response=False,
        )