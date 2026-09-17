from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from google import genai

from app.research_agent.models import (
    ResearchComprehensionEvaluation,
    ResearchStudentAnswer,
)


class ResearchComprehensionEvaluator:
    """
    Semantically evaluates a student's answer to a
    Research Agent comprehension question.

    The evaluator produces cognitive signals that can
    later be converted into CACM research evidence.

    Important:
    performance and confidence are currently heuristic
    LLM-generated assessment signals. They are not
    scientifically calibrated probabilities.
    """

    def __init__(
        self,
        model_name: str = "gemini-3.1-flash-lite-preview",
    ):
        load_dotenv()

        api_key = os.getenv(
            "GEMINI_API_KEY"
        )

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY was not found in .env"
            )

        self.model_name = model_name

        self.client = genai.Client(
            api_key=api_key
        )

    def evaluate(
        self,
        student_answer: ResearchStudentAnswer,
    ) -> ResearchComprehensionEvaluation:
        """
        Evaluate the student's conceptual understanding.

        Evaluation is semantic rather than based on exact
        string equality.
        """

        answer = (
            student_answer.answer.strip()
        )

        if not answer:
            return ResearchComprehensionEvaluation(
                is_correct=False,
                performance=0.0,
                confidence=1.0,
                feedback=(
                    "No answer was provided."
                ),
                detected_misconceptions=[],
            )

        question = (
            student_answer.question
        )

        misconception_text = (
            self._build_misconception_text(
                question.misconception_targets
            )
        )

        prompt = f"""
You are evaluating a student's conceptual answer in an
educational Research Agent.

CONCEPT:
{question.concept_name}

QUESTION:
{question.question}

EXPECTED ANSWER:
{question.correct_answer}

REFERENCE EXPLANATION:
{question.explanation}

POSSIBLE MISCONCEPTION TARGETS:
{misconception_text}

STUDENT ANSWER:
{answer}

Evaluate the student's understanding semantically.

IMPORTANT RULES:

1. Do NOT require exact wording.
2. Give credit when the student's wording expresses the
   same underlying idea as the expected answer.
3. Use only the expected answer and reference explanation
   as the basis for correctness.
4. Do not penalize the student for failing to mention
   information that the expected answer itself does not
   require.
5. Do not introduce outside facts when judging the answer.
6. Detect a misconception ONLY when the student's actual
   answer provides evidence for it.
7. Do not mark a misconception merely because it appeared
   in the possible misconception list.
8. If the answer is partially correct, use an intermediate
   performance score.
9. Confidence represents how clear the evidence in the
   student's answer is for your evaluation, NOT the
   student's confidence.
10. Keep feedback concise and educational.

Use the following interpretation for performance:

0.0 = no demonstrated understanding
0.25 = mostly incorrect with a small relevant idea
0.50 = partially correct understanding
0.75 = mostly correct understanding
1.0 = clearly demonstrates the expected understanding

is_correct should normally be true when performance is
0.75 or higher.

Confidence must be between 0.0 and 1.0.

Return ONLY valid JSON:

{{
  "is_correct": true,
  "performance": 0.75,
  "confidence": 0.9,
  "feedback": "short explanation of the evaluation",
  "detected_misconceptions": [
    "misconception actually demonstrated by the student"
  ]
}}
"""

        response = (
            self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
        )

        text = response.text

        if not text:
            raise RuntimeError(
                "Gemini returned an empty evaluation"
            )

        cleaned = (
            self._clean_json_response(
                text
            )
        )

        try:
            data = json.loads(
                cleaned
            )

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Gemini returned invalid "
                "evaluation JSON"
            ) from exc

        performance = (
            self._parse_score(
                data.get(
                    "performance",
                    0.0,
                )
            )
        )

        confidence = (
            self._parse_score(
                data.get(
                    "confidence",
                    0.0,
                )
            )
        )

        # We derive is_correct from performance ourselves.
        #
        # This prevents contradictory model output such as:
        # performance = 0.25
        # is_correct = true
        #
        # 0.75 is currently a project heuristic threshold.
        is_correct = (
            performance >= 0.75
        )

        feedback = str(
            data.get(
                "feedback",
                "",
            )
        ).strip()

        if not feedback:
            feedback = (
                "The answer was evaluated based on "
                "conceptual similarity to the expected "
                "answer."
            )

        raw_misconceptions = data.get(
            "detected_misconceptions",
            [],
        )

        misconceptions = (
            self._parse_misconceptions(
                raw_misconceptions
            )
        )

        return ResearchComprehensionEvaluation(
            is_correct=is_correct,
            performance=performance,
            confidence=confidence,
            feedback=feedback,
            detected_misconceptions=misconceptions,
        )

    @staticmethod
    def _build_misconception_text(
        misconceptions: list[str],
    ) -> str:

        if not misconceptions:
            return "None provided."

        return "\n".join(
            f"- {item}"
            for item in misconceptions
        )

    @staticmethod
    def _parse_score(
        value,
    ) -> float:
        """
        Convert a model-produced score into a safe
        number between 0 and 1.
        """

        try:
            score = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return 0.0

        return round(
            max(
                0.0,
                min(
                    1.0,
                    score,
                ),
            ),
            3,
        )

    @staticmethod
    def _parse_misconceptions(
        raw_misconceptions,
    ) -> list[str]:

        if not isinstance(
            raw_misconceptions,
            list,
        ):
            return []

        misconceptions: list[str] = []

        for item in raw_misconceptions:

            misconception = str(
                item
            ).strip()

            if (
                misconception
                and misconception
                not in misconceptions
            ):
                misconceptions.append(
                    misconception
                )

        return misconceptions

    @staticmethod
    def _clean_json_response(
        text: str,
    ) -> str:

        cleaned = text.strip()

        if cleaned.startswith(
            "```"
        ):
            lines = (
                cleaned.splitlines()
            )

            if lines:
                lines = lines[1:]

            if (
                lines
                and lines[-1]
                .strip()
                .startswith("```")
            ):
                lines = lines[:-1]

            cleaned = (
                "\n".join(
                    lines
                ).strip()
            )

        return cleaned