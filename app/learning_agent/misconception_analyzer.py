import json
import os

from dotenv import load_dotenv
from google import genai

from app.learning_agent.quiz_models import (
    QuizQuestion,
    StudentAnswer,
)


load_dotenv()


class MisconceptionAnalyzer:
    """
    Analyzes WHY a student's incorrect answer
    may have occurred.

    Gemini is used for semantic analysis, but it
    can only choose from the candidate misconceptions
    associated with the question.

    The result is treated as evidence, not absolute truth.
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
        self.client = genai.Client(
            api_key=api_key
        )

    def analyze(
        self,
        student_answer: StudentAnswer,
    ) -> list[str]:

        question: QuizQuestion = (
            student_answer.question
        )

        # If there are no candidate misconceptions,
        # there is nothing to analyze.
        if not question.misconception_targets:
            return []

        prompt = f"""
You are analyzing an incorrect student answer.

QUESTION
--------
{question.question}

EXPECTED ANSWER
---------------
{question.correct_answer}

STUDENT ANSWER
--------------
{student_answer.answer}

POSSIBLE MISCONCEPTIONS
-----------------------
{question.misconception_targets}


TASK
----
Determine which misconception, if any, is actually
supported by the student's answer.

IMPORTANT RULES:

1. You may ONLY select misconceptions from the
   provided POSSIBLE MISCONCEPTIONS list.

2. Do NOT assume that every wrong answer proves
   a misconception.

3. If the student's answer does not provide enough
   evidence to identify a misconception, return an
   empty list.

4. Select only misconceptions that are reasonably
   supported by the student's actual answer.

Return ONLY valid JSON:

{{
    "detected_misconceptions": []
}}
"""

        response = (
            self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
        )

        if not response.text:
            return []

        raw_text = response.text.strip()

        # Remove possible markdown fences
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

        except json.JSONDecodeError:
            return []

        detected = data.get(
            "detected_misconceptions",
            [],
        )

        if not isinstance(detected, list):
            return []

        # Safety check:
        # Gemini is only allowed to return
        # candidate misconceptions.
        allowed = set(
            question.misconception_targets
        )

        verified = [
            misconception
            for misconception in detected
            if misconception in allowed
        ]

        return verified