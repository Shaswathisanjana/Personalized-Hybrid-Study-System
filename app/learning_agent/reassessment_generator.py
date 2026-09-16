import json
import os

from dotenv import load_dotenv
from google import genai

from app.learning_agent.quiz_models import QuizQuestion


load_dotenv()


class ReassessmentGenerator:
    """
    Generates a new question after targeted remediation.

    The question should test the same underlying
    misconception using a different example.
    """

    def __init__(
        self,
        model_name="gemini-3.1-flash-lite-preview",
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


    def generate(
        self,
        concept_name: str,
        misconception: str,
        previous_question: str,
    ) -> QuizQuestion:

        prompt = f"""
You are generating a reassessment question.

CONCEPT
-------
{concept_name}

PREVIOUS QUESTION
-----------------
{previous_question}

MISCONCEPTION HYPOTHESIS
------------------------
{misconception}

TASK
----
Create ONE new short-answer question that tests
whether the student still shows this same
misconception.

IMPORTANT RULES
---------------
1. Do NOT repeat the previous question.
2. Use a different example.
3. Keep the question objectively gradable.
4. The question must test the same underlying skill.
5. Do not reveal the answer in the question.
6. Do not assume the misconception is definitely true.
7. The correct answer must be unambiguous.

Return ONLY valid JSON in exactly this structure:

{{
    "question": "question here",
    "correct_answer": "answer here",
    "explanation": "short step-by-step explanation"
}}
"""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )

        if not response.text:
            raise ValueError(
                "Gemini returned an empty response."
            )

        raw_text = response.text.strip()

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

        except json.JSONDecodeError as error:
            raise ValueError(
                "Gemini did not return valid JSON."
            ) from error


        question_text = str(
            data.get("question", "")
        ).strip()

        correct_answer = str(
            data.get("correct_answer", "")
        ).strip()

        explanation = str(
            data.get("explanation", "")
        ).strip()


        if not question_text:
            raise ValueError(
                "Generated question is empty."
            )

        if not correct_answer:
            raise ValueError(
                "Generated correct answer is empty."
            )


        return QuizQuestion(
            concept_name=concept_name,
            difficulty="easy",
            question=question_text,
            question_type="short_answer",
            correct_answer=correct_answer,
            explanation=explanation,

            # Important:
            # the reassessment is specifically
            # testing this hypothesis.
            misconception_targets=[
                misconception
            ],
        )