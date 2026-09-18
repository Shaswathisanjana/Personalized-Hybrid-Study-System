import json
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv
from google import genai

from app.learning_agent.quiz_models import QuizQuestion


load_dotenv()


@dataclass
class PreviousQuestion:
    """
    Lightweight description of a question already asked
    during the current practice session.

    This is supplied to Gemini only so that it can avoid
    unnecessary repetition and, when requested, generate
    a useful follow-up question.
    """

    question: str
    performance: float | None = None
    misconception_targets: list[str] = field(
        default_factory=list
    )


class GeminiQuizGenerator:
    """
    Generates structured quiz questions using Gemini.

    IMPORTANT ARCHITECTURAL BOUNDARY:

    Gemini generates educational question content.

    Gemini does NOT decide:
    - student mastery
    - student confidence
    - pedagogical action
    - target difficulty
    - whether remediation is required
    - whether the student should advance

    Those decisions remain controlled by the
    Learning Agent and CACM architecture.
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

    # =====================================================
    # PUBLIC GENERATION METHOD
    # =====================================================

    def generate(
        self,
        concept_name: str,
        difficulty: str,
        mastery: float,
        confidence: float,
        quiz_type: str = "practice_quiz",
        previous_questions: list[PreviousQuestion] | None = None,
        target_misconceptions: list[str] | None = None,
        learning_context: str | None = None,
    ) -> QuizQuestion:
        """
        Generate ONE adaptive short-answer question.

        Parameters
        ----------
        concept_name:
            Concept selected by the system.

        difficulty:
            Difficulty selected by the Learning Agent.

        mastery:
            Current CACM mastery estimate.

        confidence:
            Current CACM confidence estimate.

        quiz_type:
            Type of assessment requested by the
            Learning Agent.

        previous_questions:
            Questions already asked during the current
            practice session.

            These are used for repetition avoidance.

        target_misconceptions:
            Existing misconception hypotheses that the
            Learning Agent wants the question to probe.

            Gemini does NOT create the decision to target
            them. It only generates a question consistent
            with the supplied target.

        learning_context:
            Optional context such as:
            "Python"
            "SQL"
            "beginner Python"
            "machine learning"

            This helps maintain consistency across lesson,
            resources and assessment.
        """

        concept_name = concept_name.strip()
        difficulty = difficulty.strip().lower()

        if not concept_name:
            raise ValueError(
                "concept_name cannot be empty."
            )

        if difficulty not in {
            "easy",
            "medium",
            "hard",
        }:
            raise ValueError(
                "difficulty must be easy, medium, or hard."
            )

        previous_questions = (
            previous_questions or []
        )

        target_misconceptions = (
            target_misconceptions or []
        )

        history_text = self._build_history_text(
            previous_questions
        )

        misconception_text = (
            self._build_misconception_text(
                target_misconceptions
            )
        )

        context_text = (
            learning_context.strip()
            if learning_context
            else "No additional learning context supplied."
        )

        prompt = f"""
You are the QUESTION GENERATION COMPONENT inside an
adaptive learning system.

The Learning Agent and cognitive model have already
decided what kind of question is required.

You must follow their decision.

CURRENT LEARNING STATE

Concept:
{concept_name}

Required difficulty:
{difficulty}

Current estimated mastery:
{mastery:.3f}

Confidence in that estimate:
{confidence:.3f}

Quiz type:
{quiz_type}

Learning context:
{context_text}


PREVIOUS QUESTIONS IN THIS PRACTICE SESSION

{history_text}


MISCONCEPTION HYPOTHESES TO PROBE

{misconception_text}


TASK

Generate exactly ONE short-answer question.

The question must assess understanding of the concept,
not merely encourage the student to repeat a definition.

If previous questions exist, prefer assessing a different
aspect, representation, example, or application of the
concept.

Do NOT generate a question that is semantically equivalent
to a previous question merely by changing its wording.

Examples of BAD repetition:

Previous:
"What is the stopping condition in recursion called?"

Bad follow-up:
"What do we call the condition that stops recursion?"

These test the same thing in essentially the same way.


IMPORTANT EXCEPTION

If one or more misconception hypotheses have explicitly
been supplied, you MAY revisit the same underlying idea
when doing so is useful for targeted reassessment.

However, the new question should use a different form,
example, scenario, code fragment, application, or reasoning
task instead of simply rephrasing the previous question.

For example:

Previous question:
"What is a base case?"

Student showed confusion about base case versus recursive
step.

Useful targeted follow-up:
"Look at this recursive function and identify which line
acts as the base case and explain why."


DIFFICULTY GUIDANCE

EASY:
- basic understanding
- recognition
- simple examples
- one-step reasoning

MEDIUM:
- application
- tracing
- comparison
- explanation using an example
- small problem solving

HARD:
- deeper reasoning
- debugging
- non-obvious application
- multi-step reasoning
- edge cases


LEARNING CONTEXT RULE

If a learning context is supplied, keep the question
consistent with that context.

For example, if the context is Python, do not suddenly
generate a Java-specific question.


MISCONCEPTION RULE

The supplied misconception hypotheses are NOT guaranteed
facts about the student.

Treat them only as hypotheses that may be tested.

Do not tell the student that they definitely have a
misconception.


OUTPUT FORMAT

Return ONLY valid JSON in exactly this structure:

{{
    "question": "question shown to student",
    "correct_answer": "expected short answer",
    "explanation": "brief explanation of the answer",
    "misconception_targets": [
        "specific misconception this question can detect"
    ]
}}


FINAL RULES

- Match the required difficulty.
- Generate exactly one question.
- The answer must be objectively gradable.
- Keep the expected answer reasonably short.
- Do not reveal the answer inside the question.
- Do not put markdown around the JSON.
- Do not return commentary outside the JSON.
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

        raw_text = self._remove_code_fences(
            raw_text
        )

        try:
            data = json.loads(raw_text)

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "Gemini did not return valid JSON.\n"
                f"Received:\n{raw_text}"
            ) from exc

        self._validate_response(data)

        misconception_targets = (
            data["misconception_targets"]
        )

        if not isinstance(
            misconception_targets,
            list,
        ):
            raise RuntimeError(
                "misconception_targets must be a list."
            )

        cleaned_targets = []

        for item in misconception_targets:
            if not isinstance(item, str):
                continue

            cleaned = item.strip()

            if (
                cleaned
                and cleaned not in cleaned_targets
            ):
                cleaned_targets.append(cleaned)

        return QuizQuestion(
            concept_name=concept_name,
            difficulty=difficulty,
            question=str(
                data["question"]
            ).strip(),
            question_type="short_answer",
            correct_answer=str(
                data["correct_answer"]
            ).strip(),
            explanation=str(
                data["explanation"]
            ).strip(),
            misconception_targets=cleaned_targets,
        )

    # =====================================================
    # HISTORY FORMATTING
    # =====================================================

    def _build_history_text(
        self,
        previous_questions: list[PreviousQuestion],
    ) -> str:
        """
        Convert previous practice questions into a
        compact prompt representation.
        """

        if not previous_questions:
            return (
                "No previous questions have been asked "
                "in this practice session."
            )

        sections = []

        for index, item in enumerate(
            previous_questions,
            start=1,
        ):
            performance_text = "not available"

            if item.performance is not None:
                performance_text = (
                    f"{item.performance:.2f}"
                )

            targets = (
                ", ".join(
                    item.misconception_targets
                )
                if item.misconception_targets
                else "none"
            )

            sections.append(
                f"""
Question {index}:
{item.question}

Student performance:
{performance_text}

Misconception targets:
{targets}
""".strip()
            )

        return "\n\n".join(sections)

    # =====================================================
    # MISCONCEPTION FORMATTING
    # =====================================================

    def _build_misconception_text(
        self,
        misconceptions: list[str],
    ) -> str:
        """
        Format misconception hypotheses supplied by
        the Learning Agent.
        """

        cleaned = []

        for item in misconceptions:
            if not isinstance(item, str):
                continue

            value = item.strip()

            if value and value not in cleaned:
                cleaned.append(value)

        if not cleaned:
            return (
                "No specific misconception hypothesis "
                "has been selected for this question."
            )

        return "\n".join(
            f"- {item}"
            for item in cleaned
        )

    # =====================================================
    # RESPONSE CLEANUP
    # =====================================================

    def _remove_code_fences(
        self,
        raw_text: str,
    ) -> str:
        """
        Defensive cleanup in case Gemini returns JSON
        inside markdown code fences.
        """

        text = raw_text.strip()

        if text.startswith("```json"):
            text = text[len("```json"):]

        elif text.startswith("```"):
            text = text[len("```"):]

        if text.endswith("```"):
            text = text[:-3]

        return text.strip()

    # =====================================================
    # RESPONSE VALIDATION
    # =====================================================

    def _validate_response(
        self,
        data: dict,
    ) -> None:
        """
        Validate the minimum structured output expected
        from Gemini.
        """

        if not isinstance(data, dict):
            raise RuntimeError(
                "Gemini response must be a JSON object."
            )

        required_fields = [
            "question",
            "correct_answer",
            "explanation",
            "misconception_targets",
        ]

        for field in required_fields:
            if field not in data:
                raise RuntimeError(
                    "Gemini response is missing: "
                    f"{field}"
                )

        for field in [
            "question",
            "correct_answer",
            "explanation",
        ]:
            value = data[field]

            if (
                not isinstance(value, str)
                or not value.strip()
            ):
                raise RuntimeError(
                    f"{field} must be a non-empty string."
                )