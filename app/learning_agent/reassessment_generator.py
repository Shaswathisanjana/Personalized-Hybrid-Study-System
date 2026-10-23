import json
import os
import re
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors

from app.learning_agent.quiz_models import QuizQuestion


load_dotenv()


class ReassessmentGenerator:
    """
    Generates a targeted reassessment question after
    misconception remediation.

    Safety / reliability design:

    1. Gemini proposes a new question and answer.
    2. Our deterministic validator independently solves
       supported recurrence questions.
    3. The deterministic answer becomes authoritative.
    4. Temporary Gemini server failures are retried.
    5. If generation still fails, no fake reassessment
       result is produced.
    """

    MAX_GENERATION_ATTEMPTS = 3

    MAX_API_RETRIES = 3

    RETRY_DELAY_SECONDS = 2


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


    # ========================================================
    # PUBLIC GENERATION METHOD
    # ========================================================

    def generate(
        self,
        concept_name: str,
        misconception: str,
        previous_question: str,
    ) -> QuizQuestion:
        """
        Generate and validate a reassessment question.

        Gemini may be called multiple times if:

        - the service is temporarily unavailable
        - invalid JSON is returned
        - the generated question cannot be parsed
        - the generated question is outside the supported
          deterministic validation formats
        """

        last_error = None


        for generation_attempt in range(
            1,
            self.MAX_GENERATION_ATTEMPTS + 1,
        ):

            prompt = self._build_prompt(
                concept_name=concept_name,

                misconception=misconception,

                previous_question=previous_question,

                attempt=generation_attempt,
            )


            # ------------------------------------------------
            # CALL GEMINI WITH TEMPORARY-FAILURE RETRIES
            # ------------------------------------------------

            try:
                response_text = (
                    self._call_gemini_with_retry(
                        prompt
                    )
                )

            except RuntimeError as error:

                last_error = str(error)

                # If Gemini itself is unavailable after all
                # retries, generating another prompt will not
                # help. Stop immediately.
                break


            # ------------------------------------------------
            # PARSE GEMINI JSON
            # ------------------------------------------------

            try:
                data = self._parse_response(
                    response_text
                )

            except ValueError as error:

                last_error = str(error)

                continue


            question_text = str(
                data.get(
                    "question",
                    "",
                )
            ).strip()


            generated_answer = str(
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


            if not question_text:

                last_error = (
                    "Generated question is empty."
                )

                continue


            if not generated_answer:

                last_error = (
                    "Generated correct answer is empty."
                )

                continue


            # ------------------------------------------------
            # DETERMINISTIC VALIDATION
            # ------------------------------------------------

            validation = (
                self._validate_generated_answer(
                    question_text=question_text,

                    generated_answer=(
                        generated_answer
                    ),
                )
            )


            # ------------------------------------------------
            # QUESTION WAS VALIDATED
            # ------------------------------------------------

            if validation["validated"]:

                validated_answer = str(
                    validation[
                        "correct_answer"
                    ]
                )


                return QuizQuestion(
                    concept_name=concept_name,

                    difficulty="easy",

                    question=question_text,

                    question_type="short_answer",

                    # IMPORTANT:
                    # We use the deterministic answer,
                    # NOT Gemini's unverified answer.
                    correct_answer=(
                        validated_answer
                    ),

                    explanation=explanation,

                    misconception_targets=[
                        misconception
                    ],
                )


            # ------------------------------------------------
            # UNSUPPORTED / INVALID QUESTION
            # ------------------------------------------------

            last_error = (
                validation["reason"]
            )


        raise RuntimeError(
            "Unable to generate a safe validated "
            "reassessment question. "
            f"Reason: {last_error}"
        )


    # ========================================================
    # GEMINI API CALL WITH RETRY
    # ========================================================

    def _call_gemini_with_retry(
        self,
        prompt: str,
    ) -> str:
        """
        Call Gemini while handling temporary server failures.

        A 503 ServerError is treated as infrastructure
        failure, NOT as student failure.

        No cognitive evidence is created here.
        """

        last_error = None


        for api_attempt in range(
            1,
            self.MAX_API_RETRIES + 1,
        ):

            try:

                response = (
                    self.client.models.generate_content(
                        model=self.model_name,

                        contents=prompt,
                    )
                )


                if not response.text:

                    raise ValueError(
                        "Gemini returned an empty response."
                    )


                return response.text.strip()


            except errors.ServerError as error:

                last_error = error


                print(
                    "\nGemini service temporarily "
                    "unavailable."
                )

                print(
                    "Reassessment generation retry "
                    f"{api_attempt}/"
                    f"{self.MAX_API_RETRIES}"
                )


                if (
                    api_attempt
                    < self.MAX_API_RETRIES
                ):

                    time.sleep(
                        self.RETRY_DELAY_SECONDS
                    )


            except Exception as error:

                raise RuntimeError(
                    "Gemini reassessment generation "
                    "failed."
                ) from error


        raise RuntimeError(
            "Gemini reassessment service remained "
            "unavailable after "
            f"{self.MAX_API_RETRIES} retries."
        ) from last_error


    # ========================================================
    # PROMPT
    # ========================================================

    def _build_prompt(
        self,
        concept_name: str,
        misconception: str,
        previous_question: str,
        attempt: int,
    ) -> str:

        regeneration_note = ""


        if attempt > 1:

            regeneration_note = """
The previous generated question could not be
deterministically validated.

Generate a simpler question that follows EXACTLY
one of the supported recurrence formats below.
"""


        return f"""
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

{regeneration_note}

IMPORTANT RULES
---------------
1. Do NOT repeat the previous question.
2. Use a different numerical example.
3. Keep the question objectively gradable.
4. Test the same underlying recursive-step skill.
5. Do not reveal the answer in the question.
6. Do not assume the misconception is definitely true.
7. The correct answer must be unambiguous.
8. Keep all numbers as integers.
9. Use the function name g.
10. Use EXACTLY one of these recurrence formats.

FORMAT A

g(n) = B if n <= T,
otherwise g(n) = g(n - K) + C

FORMAT B

g(n) = B if n <= T,
otherwise g(n) = C * g(n - K)

Use small positive integers for:

B
T
K
C

The question must ask:

"What is g(X)?"

where X is a small positive integer.

Calculate the answer carefully.

Return ONLY valid JSON:

{{
    "question": "question here",
    "correct_answer": "integer answer here",
    "explanation": "short step-by-step explanation"
}}
"""


    # ========================================================
    # JSON PARSER
    # ========================================================

    def _parse_response(
        self,
        response_text: str,
    ) -> dict:

        raw_text = (
            response_text.strip()
        )


        if raw_text.startswith("```"):

            raw_text = re.sub(
                r"^```json\s*",
                "",
                raw_text,
                flags=re.IGNORECASE,
            )

            raw_text = re.sub(
                r"^```\s*",
                "",
                raw_text,
            )

            raw_text = re.sub(
                r"\s*```$",
                "",
                raw_text,
            )

            raw_text = (
                raw_text.strip()
            )


        try:

            data = json.loads(
                raw_text
            )

        except json.JSONDecodeError as error:

            raise ValueError(
                "Gemini did not return valid JSON."
            ) from error


        if not isinstance(
            data,
            dict,
        ):

            raise ValueError(
                "Gemini response must be "
                "a JSON object."
            )


        return data


    # ========================================================
    # DETERMINISTIC VALIDATOR
    # ========================================================

    def _validate_generated_answer(
        self,
        question_text: str,
        generated_answer: str,
    ) -> dict:
        """
        Independently solve supported recurrence
        questions.

        Supported forms:

        FORMAT A

        g(n) = B if n <= T
        g(n) = g(n - K) + C otherwise


        FORMAT B

        g(n) = B if n <= T
        g(n) = C * g(n - K) otherwise
        """

        normalized = (
            question_text
            .replace("×", "*")
            .replace("≤", "<=")
            .replace("\n", " ")
        )


        normalized = re.sub(
            r"\s+",
            " ",
            normalized,
        )


        # ------------------------------------------------
        # BASE CASE
        #
        # Example:
        #
        # g(n) = 2 if n <= 1
        # ------------------------------------------------

        base_match = re.search(
            r"g\s*\(\s*n\s*\)\s*=\s*"
            r"(-?\d+)"
            r"\s*if\s*n\s*<=\s*(-?\d+)",
            normalized,
            flags=re.IGNORECASE,
        )


        if not base_match:

            return {
                "validated": False,

                "correct_answer": None,

                "reason": (
                    "Base case could not "
                    "be deterministically parsed."
                ),
            }


        base_value = int(
            base_match.group(1)
        )


        threshold = int(
            base_match.group(2)
        )


        # ------------------------------------------------
        # TARGET
        #
        # Example:
        #
        # What is g(5)?
        # ------------------------------------------------

        target_matches = re.findall(
            r"what\s+is\s+"
            r"g\s*\(\s*(-?\d+)\s*\)",
            normalized,
            flags=re.IGNORECASE,
        )


        if not target_matches:

            return {
                "validated": False,

                "correct_answer": None,

                "reason": (
                    "Requested g(n) value could not "
                    "be deterministically parsed."
                ),
            }


        target_n = int(
            target_matches[-1]
        )


        # ------------------------------------------------
        # ADDITIVE FORMAT
        #
        # g(n) = g(n - K) + C
        # ------------------------------------------------

        additive_match = re.search(
            r"otherwise\s+"
            r"g\s*\(\s*n\s*\)\s*=\s*"
            r"g\s*\(\s*n\s*-\s*(\d+)\s*\)"
            r"\s*\+\s*(-?\d+)",
            normalized,
            flags=re.IGNORECASE,
        )


        if additive_match:

            step = int(
                additive_match.group(1)
            )


            constant = int(
                additive_match.group(2)
            )


            if step <= 0:

                return {
                    "validated": False,

                    "correct_answer": None,

                    "reason": (
                        "Recursive step must "
                        "be positive."
                    ),
                }


            computed_answer = (
                self._solve_additive_recurrence(
                    n=target_n,

                    threshold=threshold,

                    base_value=base_value,

                    step=step,

                    constant=constant,
                )
            )


            return (
                self._build_validation_result(
                    generated_answer=(
                        generated_answer
                    ),

                    computed_answer=(
                        computed_answer
                    ),
                )
            )


        # ------------------------------------------------
        # MULTIPLICATIVE FORMAT
        #
        # g(n) = C * g(n - K)
        # ------------------------------------------------

        multiplicative_match = re.search(
            r"otherwise\s+"
            r"g\s*\(\s*n\s*\)\s*=\s*"
            r"(-?\d+)\s*\*\s*"
            r"g\s*\(\s*n\s*-\s*(\d+)\s*\)",
            normalized,
            flags=re.IGNORECASE,
        )


        if multiplicative_match:

            constant = int(
                multiplicative_match.group(1)
            )


            step = int(
                multiplicative_match.group(2)
            )


            if step <= 0:

                return {
                    "validated": False,

                    "correct_answer": None,

                    "reason": (
                        "Recursive step must "
                        "be positive."
                    ),
                }


            computed_answer = (
                self._solve_multiplicative_recurrence(
                    n=target_n,

                    threshold=threshold,

                    base_value=base_value,

                    step=step,

                    constant=constant,
                )
            )


            return (
                self._build_validation_result(
                    generated_answer=(
                        generated_answer
                    ),

                    computed_answer=(
                        computed_answer
                    ),
                )
            )


        return {
            "validated": False,

            "correct_answer": None,

            "reason": (
                "Recursive rule could not "
                "be deterministically parsed."
            ),
        }


    # ========================================================
    # ADDITIVE SOLVER
    # ========================================================

    def _solve_additive_recurrence(
        self,
        n: int,
        threshold: int,
        base_value: int,
        step: int,
        constant: int,
    ) -> int:

        value = base_value

        current_n = n


        while current_n > threshold:

            value += constant

            current_n -= step


        return value


    # ========================================================
    # MULTIPLICATIVE SOLVER
    # ========================================================

    def _solve_multiplicative_recurrence(
        self,
        n: int,
        threshold: int,
        base_value: int,
        step: int,
        constant: int,
    ) -> int:

        value = base_value

        current_n = n


        while current_n > threshold:

            value *= constant

            current_n -= step


        return value


    # ========================================================
    # VALIDATION RESULT
    # ========================================================

    def _build_validation_result(
        self,
        generated_answer: str,
        computed_answer: int,
    ) -> dict:
        """
        Compare Gemini's proposed answer with the
        deterministic result.

        Regardless of whether Gemini was right or wrong,
        the deterministic result becomes authoritative.
        """

        generated_answer = (
            str(generated_answer)
            .strip()
        )


        try:

            generated_numeric = int(
                generated_answer
            )

        except ValueError:

            return {
                "validated": True,

                "correct_answer": (
                    computed_answer
                ),

                "reason": (
                    "Gemini answer was non-numeric. "
                    "Deterministic answer used."
                ),
            }


        if (
            generated_numeric
            != computed_answer
        ):

            print(
                "\nWARNING: Gemini generated an "
                "incorrect reassessment answer."
            )

            print(
                "Gemini answer:",
                generated_numeric,
            )

            print(
                "Validated answer:",
                computed_answer,
            )


        return {
            "validated": True,

            "correct_answer": (
                computed_answer
            ),

            "reason": (
                "Answer verified by deterministic "
                "recurrence solver."
            ),
        }