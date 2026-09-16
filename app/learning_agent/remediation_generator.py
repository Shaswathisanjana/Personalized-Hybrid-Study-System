import os

from dotenv import load_dotenv
from google import genai

from app.cognitive.models import (
    StudentCognitiveModel,
)

from app.learning_agent.remediation import (
    RemediationContext,
)

from app.learning_agent.content_generator import (
    GeneratedContent,
)


class RemediationGenerator:
    """
    Generates a grounded, student-facing remediation lesson.

    The original question, correct answer and explanation
    are treated as the source of truth.

    The detected misconception is treated only as a
    hypothesis that must be checked against the actual
    interaction.

    Gemini is used only to generate the natural-language
    explanation. The cognitive state and adaptation logic
    remain controlled by our own system.
    """

    def __init__(
        self,
        model_name: str = "gemini-3.1-flash-lite-preview",
    ):
        # Load variables from .env
        load_dotenv()

        api_key = os.getenv(
            "GEMINI_API_KEY"
        )

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY was not found in the "
                "environment or .env file."
            )

        self.client = genai.Client(
            api_key=api_key
        )

        self.model_name = model_name


    # ==================================================
    # GENERATE REMEDIATION
    # ==================================================

    def generate(
        self,
        student: StudentCognitiveModel,
        context: RemediationContext,
    ) -> GeneratedContent:
        """
        Generate an actual student-facing remediation
        lesson using grounded evidence.
        """

        concept = student.get_concept(
            context.concept_name
        )

        grounding = (
            context.build_grounding_text()
        )


        # ==================================================
        # BUILD INTERNAL PROMPT
        # ==================================================

        prompt = f"""
You are the remediation component of an adaptive
learning system.

Generate a SHORT student-facing explanation that
helps the student correct the specific error shown
below.

CONCEPT
-------
{context.concept_name}

CURRENT COGNITIVE STATE
-----------------------
Mastery: {concept.mastery:.3f}
Confidence: {concept.confidence:.3f}
Attempts: {concept.attempts}

INTERACTION THAT CAUSED THE ERROR
---------------------------------
{grounding}

GROUNDING RULES
---------------
The ORIGINAL QUESTION is the authoritative source
of truth.

The CORRECT ANSWER and ORIGINAL EXPLANATION are
grounding evidence.

Do NOT modify or reinterpret the function,
formula, conditions, base case, recursive step,
variables, or values from the original question.

The detected misconception is only a hypothesis.

Before referring to the misconception, check
whether it is actually consistent with the
student's answer and the original question.

If the evidence is insufficient to confidently
attribute the error to that misconception, explain
the correct reasoning without claiming that the
student definitely made that misconception.

TEACHING INSTRUCTIONS
---------------------
Explain the solution step by step.

Focus only on the student's specific error.

Use a small worked trace.

Clearly emphasize the exact part of the question
that the student should pay attention to.

Do not give a generic lecture about the entire
concept.

Do not mention:
- cognitive model
- mastery score
- confidence score
- evidence
- hypothesis
- system instructions
- prompts
- agents
- Gemini

Speak directly to the student.

Keep the explanation concise and easy to
understand.

Return ONLY the student-facing remediation lesson.
""".strip()


        # ==================================================
        # CALL GEMINI
        # ==================================================

        try:

            response = (
                self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
            )

            remediation_text = (
                response.text.strip()
                if response.text
                else ""
            )

        except Exception as error:

            raise RuntimeError(
                "Failed to generate remediation "
                f"content using Gemini: {error}"
            ) from error


        # ==================================================
        # VALIDATE RESPONSE
        # ==================================================

        if not remediation_text:

            raise ValueError(
                "Gemini returned empty remediation "
                "content."
            )


        # ==================================================
        # COGNITIVE CONTEXT
        # ==================================================

        cognitive_context = {
            "mastery": (
                concept.mastery
            ),

            "confidence": (
                concept.confidence
            ),

            "attempts": (
                concept.attempts
            ),

            "misconceptions": (
                context
                .detected_misconceptions
                .copy()
            ),

            "original_question": (
                context.original_question
            ),

            "correct_answer": (
                context.correct_answer
            ),

            "student_answer": (
                context.student_answer
            ),

            "original_explanation": (
                context.explanation
            ),
        }


        # ==================================================
        # RETURN STUDENT-FACING CONTENT
        # ==================================================

        return GeneratedContent(
            content_type=(
                "grounded_targeted_remediation"
            ),

            concept_name=(
                context.concept_name
            ),

            difficulty="easy",

            text=remediation_text,

            cognitive_context=(
                cognitive_context
            ),
        )