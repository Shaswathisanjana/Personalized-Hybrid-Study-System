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

    Gemini performs semantic analysis using:

    - the original question
    - the correct answer
    - the worked explanation
    - the student's answer
    - predefined candidate misconceptions

    Gemini is NOT allowed to invent a new
    misconception.

    The result is treated as a hypothesis/evidence,
    not as absolute truth.
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


    # ==================================================
    # ANALYZE STUDENT ANSWER
    # ==================================================

    def analyze(
        self,
        student_answer: StudentAnswer,
    ) -> list[str]:
        """
        Determine whether the student's incorrect
        answer supports one or more predefined
        misconception hypotheses.

        Returns:
            list[str]

        Example:

        [
            "Confuses n-2 recursive step with n-1"
        ]

        If there is not enough evidence:

        []
        """

        question: QuizQuestion = (
            student_answer.question
        )


        # ------------------------------------------------
        # NO CANDIDATE MISCONCEPTIONS
        # ------------------------------------------------

        if not question.misconception_targets:
            return []


        # ------------------------------------------------
        # BUILD CANDIDATE LIST
        # ------------------------------------------------

        candidate_text = "\n".join(
            f"- {misconception}"
            for misconception
            in question.misconception_targets
        )


        # ------------------------------------------------
        # PROMPT
        # ------------------------------------------------

        prompt = f"""
You are analyzing a student's incorrect answer to
identify whether it provides evidence for a specific
misconception hypothesis.

The ORIGINAL QUESTION is the source of truth.

Do not modify or reinterpret the mathematical
definition given in the question.


ORIGINAL QUESTION
-----------------
{question.question}


CORRECT ANSWER
--------------
{question.correct_answer}


WORKED EXPLANATION
------------------
{question.explanation}


STUDENT ANSWER
--------------
{student_answer.answer}


CANDIDATE MISCONCEPTIONS
------------------------
{candidate_text}


YOUR TASK
---------
Analyze the student's answer using the following
procedure.

STEP 1:
Understand the exact mathematical or conceptual
structure of the ORIGINAL QUESTION.

STEP 2:
Use the CORRECT ANSWER and WORKED EXPLANATION to
understand the intended reasoning.

STEP 3:
For each candidate misconception, determine what
reasoning or result would plausibly follow if the
student actually held that misconception.

STEP 4:
Compare that predicted reasoning/result with the
student's actual answer.

STEP 5:
Select a candidate misconception only when the
student's answer provides reasonable evidence for it.


IMPORTANT RULES
---------------
1. The ORIGINAL QUESTION is authoritative.

2. Never change the formula, recursive step,
   base case, values, or other facts from the
   original question.

3. You may ONLY select an item appearing exactly
   in the CANDIDATE MISCONCEPTIONS list.

4. Do NOT invent new misconceptions.

5. A wrong answer alone is NOT enough evidence
   for a misconception.

6. If multiple unrelated mistakes could reasonably
   produce the student's answer, and the candidate
   cannot be distinguished, return an empty list.

7. If the student's answer is reasonably consistent
   with one of the candidate misconceptions, select
   that candidate.

8. Treat the selected misconception as a hypothesis,
   not as proven fact.

9. Do not include explanations in the final response.

Return ONLY valid JSON in exactly this structure:

{{
    "detected_misconceptions": []
}}

or, when supported:

{{
    "detected_misconceptions": [
        "exact candidate misconception"
    ]
}}
"""


        # ------------------------------------------------
        # GEMINI CALL
        # ------------------------------------------------

        try:
            response = (
                self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
            )

        except Exception:
            # Misconception analysis should not crash
            # the entire learning pipeline if the LLM
            # request fails.
            return []


        # ------------------------------------------------
        # EMPTY RESPONSE
        # ------------------------------------------------

        if not response.text:
            return []


        raw_text = (
            response.text.strip()
        )


        # ------------------------------------------------
        # REMOVE POSSIBLE MARKDOWN CODE FENCES
        # ------------------------------------------------

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

            raw_text = (
                raw_text.strip()
            )


        # ------------------------------------------------
        # PARSE JSON
        # ------------------------------------------------

        try:
            data = json.loads(
                raw_text
            )

        except json.JSONDecodeError:
            return []


        # ------------------------------------------------
        # VALIDATE STRUCTURE
        # ------------------------------------------------

        detected = data.get(
            "detected_misconceptions",
            [],
        )


        if not isinstance(
            detected,
            list,
        ):
            return []


        # ------------------------------------------------
        # SAFETY VALIDATION
        # ------------------------------------------------
        #
        # Even if Gemini ignores the prompt and invents
        # a misconception, it will be rejected here.
        # ------------------------------------------------

        allowed = set(
            question.misconception_targets
        )


        verified = []

        for misconception in detected:

            if (
                isinstance(
                    misconception,
                    str,
                )
                and misconception in allowed
                and misconception not in verified
            ):

                verified.append(
                    misconception
                )


        return verified