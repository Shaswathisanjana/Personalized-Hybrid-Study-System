import json
import os
import re

from dotenv import load_dotenv
from google import genai

from app.learning_agent.quiz_models import (
    StudentAnswer,
    EvaluationResult,
)


load_dotenv()


class AnswerEvaluator:
    """
    Hybrid evaluator for student short-answer responses.

    Evaluation strategy:

        Student answer
            |
            v
        Normalize text
            |
            v
        Exact normalized match?
            |
        YES ---------> Correct
            |
            NO
            v
        Semantic evaluation using Gemini
            |
            v
        correct / partially_correct / incorrect

    Gemini is used only to interpret semantic equivalence.

    The evaluator does NOT update mastery or confidence.
    Cognitive-state updates remain the responsibility
    of the CACM CognitiveEngine.
    """

    VALID_JUDGMENTS = {
        "correct",
        "partially_correct",
        "incorrect",
    }

    PERFORMANCE_MAP = {
        "correct": 1.0,
        "partially_correct": 0.5,
        "incorrect": 0.0,
    }

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

    # ==================================================
    # PUBLIC EVALUATION METHOD
    # ==================================================

    def evaluate(
        self,
        student_answer: StudentAnswer,
    ) -> EvaluationResult:
        """
        Evaluate one student answer.

        Exact normalized matches are handled
        deterministically.

        Non-exact answers are evaluated semantically
        against the expected answer.
        """

        if not isinstance(
            student_answer,
            StudentAnswer,
        ):
            raise TypeError(
                "student_answer must be a StudentAnswer."
            )

        expected = (
            student_answer.question.correct_answer.strip()
        )

        received = (
            student_answer.answer.strip()
        )

        if not expected:
            raise ValueError(
                "The question does not contain a "
                "correct_answer."
            )

        if not received:
            return EvaluationResult(
                is_correct=False,
                performance=0.0,
                feedback=(
                    "No answer was provided."
                ),
                detected_misconceptions=[],
            )

        # ==================================================
        # STEP 1
        # DETERMINISTIC NORMALIZED MATCH
        # ==================================================

        normalized_expected = self._normalize(
            expected
        )

        normalized_received = self._normalize(
            received
        )

        if (
            normalized_received
            == normalized_expected
        ):
            return EvaluationResult(
                is_correct=True,
                performance=1.0,
                feedback="Correct answer.",
                detected_misconceptions=[],
            )

        # ==================================================
        # STEP 2
        # SEMANTIC EVALUATION
        # ==================================================

        return self._semantic_evaluate(
            student_answer=student_answer,
        )

    # ==================================================
    # SEMANTIC EVALUATION
    # ==================================================

    def _semantic_evaluate(
        self,
        student_answer: StudentAnswer,
    ) -> EvaluationResult:
        """
        Ask Gemini to compare the student's meaning
        with the reference answer.

        Gemini must return a structured judgment rather
        than directly changing any cognitive state.
        """

        question = (
            student_answer.question.question.strip()
        )

        expected = (
            student_answer.question.correct_answer.strip()
        )

        received = (
            student_answer.answer.strip()
        )

        explanation = (
            student_answer.question.explanation.strip()
        )

        prompt = f"""
You are an answer evaluator inside an adaptive
educational system.

Evaluate the STUDENT ANSWER using the QUESTION and
REFERENCE ANSWER.

QUESTION:
{question}

REFERENCE ANSWER:
{expected}

REFERENCE EXPLANATION:
{explanation}

STUDENT ANSWER:
{received}

Classify the answer as exactly ONE of:

"correct"
"partially_correct"
"incorrect"

Definitions:

correct:
The student's answer expresses the essential meaning
required by the reference answer. Different wording is
allowed.

partially_correct:
The answer demonstrates some correct understanding but
misses an important required idea, is incomplete, or
contains a minor conceptual error.

incorrect:
The answer does not demonstrate the required
understanding, contradicts the reference answer, or is
substantially wrong.

Important rules:

- Judge meaning, not wording.
- Do not require exact phrase matching.
- Do not reward irrelevant text.
- Do not assume information the student did not state.
- Do not change the reference answer.
- Do not invent a new expected answer.
- Keep feedback concise.
- Do not include markdown.
- Do not reveal hidden reasoning.

Return ONLY valid JSON using exactly this structure:

{{
    "judgment": "correct",
    "feedback": "Short student-facing explanation."
}}
"""

        try:

            response = (
                self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
            )

        except Exception as exc:
            raise RuntimeError(
                "Semantic answer evaluation failed."
            ) from exc

        if not response.text:
            raise RuntimeError(
                "Gemini returned an empty evaluation."
            )

        raw_text = response.text.strip()

        # ------------------------------------------------
        # Defensive cleanup if Gemini adds code fences
        # ------------------------------------------------

        if raw_text.startswith("```"):

            raw_text = re.sub(
                r"^```(?:json)?",
                "",
                raw_text,
                flags=re.IGNORECASE,
            )

            raw_text = re.sub(
                r"```$",
                "",
                raw_text,
            )

            raw_text = raw_text.strip()

        # ------------------------------------------------
        # Parse structured response
        # ------------------------------------------------

        try:

            data = json.loads(
                raw_text
            )

        except json.JSONDecodeError as exc:

            raise RuntimeError(
                "Gemini did not return valid JSON "
                "during answer evaluation.\n"
                f"Received:\n{raw_text}"
            ) from exc

        judgment = str(
            data.get(
                "judgment",
                "",
            )
        ).strip().lower()

        feedback = str(
            data.get(
                "feedback",
                "",
            )
        ).strip()

        if judgment not in self.VALID_JUDGMENTS:
            raise RuntimeError(
                "Gemini returned an invalid "
                f"judgment: {judgment}"
            )

        if not feedback:

            feedback = (
                "Answer evaluation completed."
            )

        performance = (
            self.PERFORMANCE_MAP[
                judgment
            ]
        )

        return EvaluationResult(
            is_correct=(
                judgment == "correct"
            ),
            performance=performance,
            feedback=feedback,
            detected_misconceptions=[],
        )

    # ==================================================
    # TEXT NORMALIZATION
    # ==================================================

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:
        """
        Normalize text before deterministic comparison.

        Example:

            "Base Case!"
                ->
            "base case"
        """

        text = text.strip().lower()

        # Replace punctuation with spaces.
        text = re.sub(
            r"[^a-z0-9+#]+",
            " ",
            text,
        )

        # Collapse repeated whitespace.
        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()