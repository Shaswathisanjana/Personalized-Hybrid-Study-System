import json
import os

from dotenv import load_dotenv
from google import genai

from app.learning_agent.quiz_models import QuizQuestion


load_dotenv()


class GeminiQuizGenerator:
    """
    Generates structured quiz questions using Gemini.

    Gemini generates the educational question and answer,
    but the Learning Agent controls which concept and
    difficulty should be used.
    """

    def __init__(
        self,
        model_name: str = "gemini-3.1-flash-lite-preview",
    ):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY was not found."
            )

        self.model_name = model_name
        self.client = genai.Client(api_key=api_key)

    def generate(
        self,
        concept_name: str,
        difficulty: str,
        mastery: float,
        confidence: float,
        quiz_type: str = "practice_quiz",
    ) -> QuizQuestion:

        prompt = f"""
You are generating ONE question for an adaptive
learning system.

Concept: {concept_name}
Difficulty: {difficulty}
Student mastery: {mastery:.3f}
Confidence in mastery estimate: {confidence:.3f}
Quiz type: {quiz_type}

Generate one short-answer question.

Return ONLY valid JSON in exactly this structure:

{{
    "question": "question shown to student",
    "correct_answer": "expected short answer",
    "explanation": "brief explanation of the answer",
    "misconception_targets": [
        "specific misconception this question can detect"
    ]
}}

Rules:
- Match the requested difficulty.
- The answer must be objectively gradable.
- Keep the expected answer short.
- Do not put markdown around the JSON.
- Do not reveal the correct answer inside the question.
"""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )

        if not response.text:
            raise RuntimeError(
                "Gemini returned an empty response."
            )

        raw_text = response.text.strip()

        # Defensive cleanup in case Gemini adds
        # markdown code fences.
        if raw_text.startswith("```"):
            raw_text = raw_text.replace(
                "```json",
                "",
                1,
            )

            raw_text = raw_text.replace(
                "```",
                "",
            )

            raw_text = raw_text.strip()

        try:
            data = json.loads(raw_text)

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Gemini did not return valid JSON.\n"
                f"Received:\n{raw_text}"
            ) from exc

        required_fields = [
            "question",
            "correct_answer",
            "explanation",
            "misconception_targets",
        ]

        for field in required_fields:
            if field not in data:
                raise RuntimeError(
                    f"Gemini response is missing: {field}"
                )

        return QuizQuestion(
            concept_name=concept_name,
            difficulty=difficulty,
            question=data["question"],
            question_type="short_answer",
            correct_answer=data["correct_answer"],
            explanation=data["explanation"],
            misconception_targets=data[
                "misconception_targets"
            ],
        )