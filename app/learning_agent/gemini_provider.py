import os

from dotenv import load_dotenv
from google import genai

from app.learning_agent.content_provider import ContentProvider
from app.learning_agent.content_generator import GeneratedContent


load_dotenv()


class GeminiContentProvider(ContentProvider):
    """
    Gemini generates student-facing educational content.

    Gemini does NOT decide:
    - the student's mastery
    - the next pedagogical action
    - whether a cognitive conflict exists
    - the activity difficulty

    Those decisions are controlled by our
    cognitive architecture and Learning Agent.
    """

    def __init__(
        self,
        model_name: str = "gemini-3.1-flash-lite-preview",
    ):
        self.model_name = model_name

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY was not found."
            )

        self.client = genai.Client(
            api_key=api_key
        )

    def create_content(
        self,
        request: GeneratedContent,
    ) -> str:

        context = request.cognitive_context

        mastery = context.get("mastery", 0.5)
        confidence = context.get("confidence", 0.0)
        attempts = context.get("attempts", 0)
        misconceptions = context.get(
            "misconceptions",
            []
        )

        prompt = f"""
You are the content generation component of a
personalized AI tutoring system.

IMPORTANT:
The pedagogical decision has already been made
by another agent.

Do NOT change the activity type.
Do NOT change the difficulty.

STUDENT COGNITIVE STATE

Concept:
{request.concept_name}

Estimated mastery:
{mastery:.3f}

Confidence in mastery estimate:
{confidence:.3f}

Previous attempts:
{attempts}

Known misconceptions:
{misconceptions}


LEARNING AGENT DECISION

Activity type:
{request.content_type}

Difficulty:
{request.difficulty}


PERSONALIZATION INSTRUCTION

{request.text}


GENERATION RULES

If activity type is teach_concept:
- Explain the concept directly to the student.
- Match the requested difficulty.
- Use simple language when mastery is low.
- Include one clear example.
- Keep the explanation concise.

If activity type is practice_quiz:
- Generate exactly ONE practice question.
- Match the requested difficulty.
- Do not provide the answer.
- Do not provide hints unless requested.

If activity type is diagnostic_quiz:
- Generate exactly ONE diagnostic question.
- Test conceptual understanding rather than recall.
- Do not provide the answer.

If activity type is verification_quiz:
- Generate exactly ONE challenging question.
- Test whether the student can independently apply
  the concept.
- Do not provide the answer.

If activity type is advance_topic:
- Introduce one suitable advanced application
  or closely related concept.

Return ONLY the content that should be shown
to the student.
"""

        try:
            response = (
                self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
            )

            if not response.text:
                raise RuntimeError(
                    "Gemini returned empty content."
                )

            return response.text.strip()

        except Exception as exc:
            raise RuntimeError(
                f"Gemini generation failed: {exc}"
            ) from exc