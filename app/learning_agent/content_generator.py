from dataclasses import dataclass

from app.cognitive.models import (
    StudentCognitiveModel,
)

from app.learning_agent.agent import (
    LearningAction,
)


@dataclass
class GeneratedContent:
    content_type: str
    concept_name: str
    difficulty: str
    text: str
    cognitive_context: dict


class PersonalizedContentGenerator:
    """
    Converts a Learning Agent decision into a
    personalized content request.

    This class does NOT generate the final lesson.
    It prepares cognitive context that can later
    be given to a content provider such as Gemini.
    """

    def generate(
        self,
        student: StudentCognitiveModel,
        action: LearningAction,
    ) -> GeneratedContent:

        concept = student.get_concept(
            action.concept_name
        )

        misconceptions = (
            concept.misconceptions.copy()
        )

        cognitive_context = {
            "mastery": concept.mastery,
            "confidence": concept.confidence,
            "attempts": concept.attempts,
            "misconceptions": misconceptions,
        }


        # ==============================================
        # TARGETED REMEDIATION
        # ==============================================

        if (
            action.action_type == "teach_concept"
            and misconceptions
        ):

            misconception_text = "; ".join(
                misconceptions
            )

            text = (
                f"Teach {action.concept_name} at "
                f"{action.difficulty} difficulty. "
                f"The student currently has mastery "
                f"{concept.mastery:.3f} and confidence "
                f"{concept.confidence:.3f}. "
                f"The following misconception has been "
                f"detected: {misconception_text}. "
                f"Focus the explanation specifically on "
                f"correcting this misconception. "
                f"Do not provide only a generic explanation. "
                f"Contrast the incorrect reasoning with the "
                f"correct reasoning and include one simple "
                f"worked example."
            )

            return GeneratedContent(
                content_type="targeted_remediation",
                concept_name=action.concept_name,
                difficulty=action.difficulty,
                text=text,
                cognitive_context=cognitive_context,
            )


        # ==============================================
        # NORMAL TEACHING
        # ==============================================

        if action.action_type == "teach_concept":

            text = (
                f"Teach {action.concept_name} at "
                f"{action.difficulty} difficulty. "
                f"The student's current mastery is "
                f"{concept.mastery:.3f}. "
                f"Use a simple explanation followed by "
                f"one worked example."
            )


        # ==============================================
        # PRACTICE QUIZ
        # ==============================================

        elif action.action_type == "practice_quiz":

            text = (
                f"Create a {action.difficulty} practice "
                f"question for {action.concept_name}. "
                f"The student's current mastery is "
                f"{concept.mastery:.3f}. "
                f"The question should strengthen the "
                f"student's understanding."
            )


        # ==============================================
        # DIAGNOSTIC QUIZ
        # ==============================================

        elif action.action_type == "diagnostic_quiz":

            text = (
                f"Create a diagnostic question for "
                f"{action.concept_name}. "
                f"The question should help determine "
                f"the student's actual understanding "
                f"because conflicting evidence exists."
            )


        # ==============================================
        # VERIFICATION QUIZ
        # ==============================================

        elif action.action_type == "verification_quiz":

            text = (
                f"Create a {action.difficulty} verification "
                f"question for {action.concept_name}. "
                f"Mastery appears high, but confidence in "
                f"the estimate is still low. "
                f"Use a question that requires deeper "
                f"understanding rather than simple recall."
            )


        # ==============================================
        # ADVANCE TOPIC
        # ==============================================

        elif action.action_type == "advance_topic":

            text = (
                f"The student has demonstrated strong "
                f"understanding of {action.concept_name}. "
                f"Prepare material that progresses toward "
                f"a more advanced application of the topic."
            )


        # ==============================================
        # FALLBACK
        # ==============================================

        else:

            text = (
                f"Prepare learning material for "
                f"{action.concept_name}."
            )


        return GeneratedContent(
            content_type=action.action_type,
            concept_name=action.concept_name,
            difficulty=action.difficulty,
            text=text,
            cognitive_context=cognitive_context,
        )