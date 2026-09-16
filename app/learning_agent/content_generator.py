from dataclasses import dataclass

from app.cognitive.models import StudentCognitiveModel
from app.learning_agent.agent import LearningAction


@dataclass
class GeneratedContent:
    """
    Structured content generated for a student.
    """

    content_type: str
    concept_name: str
    difficulty: str
    text: str
    cognitive_context: dict


class PersonalizedContentGenerator:
    """
    Generates personalized learning content using
    information from the shared cognitive model.

    For now this uses local generation rules.
    Later the actual text-generation step can be
    replaced by Gemini while preserving the
    cognitive personalization logic.
    """

    def generate(
        self,
        student: StudentCognitiveModel,
        action: LearningAction,
    ) -> GeneratedContent:

        concept = student.get_concept(
            action.concept_name
        )

        context = {
            "mastery": concept.mastery,
            "confidence": concept.confidence,
            "attempts": concept.attempts,
            "misconceptions": concept.misconceptions,
        }

        if action.action_type == "teach_concept":
            text = self._generate_lesson(
                action,
                context,
            )

        elif action.action_type == "practice_quiz":
            text = self._generate_practice(
                action,
                context,
            )

        elif action.action_type == "diagnostic_quiz":
            text = self._generate_diagnostic(
                action,
                context,
            )

        elif action.action_type == "verification_quiz":
            text = self._generate_verification(
                action,
                context,
            )

        elif action.action_type == "advance_topic":
            text = self._generate_advanced_content(
                action,
                context,
            )

        else:
            raise ValueError(
                f"Unsupported action: {action.action_type}"
            )

        return GeneratedContent(
            content_type=action.action_type,
            concept_name=action.concept_name,
            difficulty=action.difficulty,
            text=text,
            cognitive_context=context,
        )

    def _generate_lesson(
        self,
        action,
        context,
    ):
        return (
            f"Personalized lesson for {action.concept_name}. "
            f"The student's current mastery is "
            f"{context['mastery']:.2f}. "
            f"Start with fundamentals and simple examples "
            f"before introducing more difficult applications."
        )

    def _generate_practice(
        self,
        action,
        context,
    ):
        return (
            f"Generate a {action.difficulty} practice problem "
            f"for {action.concept_name}. "
            f"The student's mastery is "
            f"{context['mastery']:.2f}, so the problem should "
            f"reinforce understanding without introducing "
            f"unnecessary complexity."
        )

    def _generate_diagnostic(
        self,
        action,
        context,
    ):
        return (
            f"Create a diagnostic question for "
            f"{action.concept_name}. "
            f"The question should distinguish between "
            f"memorized knowledge and the ability to "
            f"apply the concept independently."
        )

    def _generate_verification(
        self,
        action,
        context,
    ):
        return (
            f"Create a challenging verification problem for "
            f"{action.concept_name}. "
            f"Current mastery is high but confidence in the "
            f"estimate is only {context['confidence']:.2f}. "
            f"Use the result to verify the mastery estimate."
        )

    def _generate_advanced_content(
        self,
        action,
        context,
    ):
        return (
            f"The student has demonstrated strong understanding "
            f"of {action.concept_name}. "
            f"Introduce a more advanced application or "
            f"closely related concept."
        )