from __future__ import annotations

import json
import os

from dotenv import load_dotenv
from google import genai

from app.research_agent.models import (
    ResearchComprehensionQuestion,
    ResearchSynthesis,
)


class ResearchComprehensionGenerator:
    """
    Generates a comprehension question from a grounded
    ResearchSynthesis.

    The purpose is not to test memorization of paper names.
    It tests whether the student understood the underlying
    concept presented during the research interaction.
    """

    VALID_DIFFICULTIES = {
        "easy",
        "medium",
        "hard",
    }

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

    def generate(
        self,
        synthesis: ResearchSynthesis,
        concept_name: str,
        difficulty: str = "medium",
    ) -> ResearchComprehensionQuestion:
        """
        Generate one comprehension question grounded in
        the supplied research synthesis.
        """

        concept_name = (
            concept_name.strip()
        )

        difficulty = (
            difficulty.strip().lower()
        )

        if not concept_name:
            raise ValueError(
                "Concept name cannot be empty"
            )

        if difficulty not in self.VALID_DIFFICULTIES:
            raise ValueError(
                "Difficulty must be easy, medium, or hard"
            )

        if not synthesis.answer.strip():
            raise ValueError(
                "Research synthesis cannot be empty"
            )

        evidence_text = (
            self._build_evidence_text(
                synthesis
            )
        )

        prompt = f"""
You are the comprehension-assessment component of an
educational Research Agent.

The student has just studied the following grounded
research synthesis.

CONCEPT:
{concept_name}

RESEARCH QUESTION:
{synthesis.question}

SYNTHESIS:
{synthesis.answer}

SUPPORTING EVIDENCE:
{evidence_text}

Create ONE comprehension question that tests whether the
student actually understood the concept.

DIFFICULTY:
{difficulty}

STRICT RULES:

1. The question must be answerable using only the supplied
   synthesis and evidence.
2. Do not require outside knowledge.
3. Do not ask for paper titles, author names, years, URLs,
   or citation memorization.
4. Test conceptual understanding rather than simple
   word-for-word recall.
5. The correct answer must be directly supported by the
   supplied synthesis/evidence.
6. Do not invent facts.
7. Keep the question appropriate for the requested
   difficulty.
8. Identify likely misconceptions that a wrong answer
   could reveal.

Return ONLY valid JSON:

{{
  "question": "question for the student",
  "correct_answer": "expected conceptual answer",
  "explanation": "why this answer is correct based only on the supplied material",
  "misconception_targets": [
    "possible misconception"
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
                "Gemini returned an empty "
                "comprehension question"
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
                "comprehension-question JSON"
            ) from exc

        question = str(
            data.get(
                "question",
                "",
            )
        ).strip()

        correct_answer = str(
            data.get(
                "correct_answer",
                "",
            )
        ).strip()

        explanation = str(
            data.get(
                "explanation",
                "",
            )
        ).strip()

        raw_misconceptions = data.get(
            "misconception_targets",
            [],
        )

        if not question:
            raise RuntimeError(
                "Generated question was empty"
            )

        if not correct_answer:
            raise RuntimeError(
                "Generated correct answer was empty"
            )

        if not explanation:
            raise RuntimeError(
                "Generated explanation was empty"
            )

        misconceptions: list[str] = []

        if isinstance(
            raw_misconceptions,
            list,
        ):
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

        return ResearchComprehensionQuestion(
            concept_name=concept_name,
            question=question,
            correct_answer=correct_answer,
            explanation=explanation,
            difficulty=difficulty,
            misconception_targets=misconceptions,
        )

    @staticmethod
    def _build_evidence_text(
        synthesis: ResearchSynthesis,
    ) -> str:

        if not synthesis.evidence:
            return (
                "No separate evidence items were "
                "provided."
            )

        sections: list[str] = []

        for index, item in enumerate(
            synthesis.evidence,
            start=1,
        ):
            sections.append(
                f"{index}. {item.claim}"
            )

        return "\n".join(
            sections
        )

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