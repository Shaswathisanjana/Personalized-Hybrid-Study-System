import json
import os

from dotenv import load_dotenv
from google import genai

from app.coding_agent.models import (
    CodingSubmission,
    CodingEvaluation,
    CodingTestResult,
)

from app.coding_agent.static_analyzer import (
    CodingStaticAnalyzer,
)

from app.coding_agent.code_runner import (
    ControlledCodeRunner,
    BehavioralTestCase,
)


load_dotenv()


class CodingEvaluator:
    """
    Hybrid evaluator for student programming submissions.

    Evaluation combines:

    1. Static AST analysis
    2. Behavioral test execution
    3. Gemini semantic reasoning

    Gemini interprets objective evidence produced by
    the first two components. It does not execute code.
    """

    def __init__(
        self,
        model_name: str = "gemini-3.1-flash-lite-preview",
        static_analyzer=None,
        code_runner=None,
    ):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY was not found "
                "in the environment."
            )

        self.client = genai.Client(
            api_key=api_key
        )

        self.model_name = model_name

        self.static_analyzer = (
            static_analyzer
            or CodingStaticAnalyzer()
        )

        self.code_runner = (
            code_runner
            or ControlledCodeRunner()
        )

    def evaluate(
        self,
        submission: CodingSubmission,
        test_cases: list[BehavioralTestCase],
    ) -> CodingEvaluation:
        """
        Evaluate one coding submission.
        """

        if not isinstance(
            submission,
            CodingSubmission,
        ):
            raise TypeError(
                "submission must be a CodingSubmission."
            )

        # ==================================================
        # 1. STATIC ANALYSIS
        # ==================================================

        static_result = (
            self.static_analyzer.analyze(
                submission.code
            )
        )

        # Syntax errors are objective.
        # There is no reason to run behavioral tests or ask
        # Gemini to judge correctness when code cannot parse.
        if not static_result.syntax_valid:

            return CodingEvaluation(
                is_correct=False,
                performance=0.0,
                confidence=1.0,
                feedback=(
                    "The submitted code contains a "
                    "Python syntax error: "
                    + static_result.syntax_error
                ),
                test_results=[],
                detected_misconceptions=[],
            )

        # ==================================================
        # 2. BEHAVIORAL TESTING
        # ==================================================

        behavioral_result = (
            self.code_runner.run_tests(
                code=submission.code,
                test_cases=test_cases,
            )
        )

        coding_test_results = [
            CodingTestResult(
                test_name=result.test_name,
                passed=result.passed,
                expected_output=(
                    result.expected_output
                ),
                actual_output=(
                    result.actual_output
                ),
                error=result.error,
            )
            for result in behavioral_result.tests
        ]

        # ==================================================
        # 3. PREPARE OBJECTIVE EVIDENCE FOR GEMINI
        # ==================================================

        behavioral_summary = []

        for result in behavioral_result.tests:

            behavioral_summary.append(
                {
                    "test_name": result.test_name,
                    "passed": result.passed,
                    "expected_output": (
                        result.expected_output
                    ),
                    "actual_output": (
                        result.actual_output
                    ),
                    "error": result.error,
                }
            )

        objective_evidence = {
            "syntax_valid": (
                static_result.syntax_valid
            ),
            "function_names": (
                static_result.function_names
            ),
            "has_recursion": (
                static_result.has_recursion
            ),
            "has_loop": (
                static_result.has_loop
            ),
            "has_return": (
                static_result.has_return
            ),
            "recursive_functions": (
                static_result.recursive_functions
            ),
            "behavioral_pass_rate": (
                behavioral_result.pass_rate
            ),
            "timed_out": (
                behavioral_result.timed_out
            ),
            "execution_error": (
                behavioral_result.execution_error
            ),
            "tests": behavioral_summary,
        }

        task = submission.task

        # ==================================================
        # 4. SEMANTIC INTERPRETATION
        # ==================================================

        prompt = f"""
You are the semantic reasoning component of an
educational Coding Agent.

Your job is to evaluate what the student's submitted
code demonstrates about their understanding of the
target programming concept.

TARGET CONCEPT:
{task.concept_name}

TASK TITLE:
{task.title}

TASK DESCRIPTION:
{task.description}

DIFFICULTY:
{task.difficulty}

EXPECTED BEHAVIOR:
{task.expected_behavior}

POSSIBLE MISCONCEPTION TARGETS:
{json.dumps(task.misconception_targets)}

STUDENT CODE:
--- BEGIN STUDENT CODE ---
{submission.code}
--- END STUDENT CODE ---

OBJECTIVE STATIC AND BEHAVIORAL EVIDENCE:
{json.dumps(objective_evidence, indent=2)}

IMPORTANT RULES:

1. Do NOT invent test results.

2. Treat the supplied objective evidence as authoritative.

3. A program producing correct output does NOT
   automatically demonstrate the requested concept.

   Example:
   if the task specifically requires recursion but the
   student solves it using a loop, the solution should
   not receive full conceptual performance.

4. detected_misconceptions must only contain
   misconceptions that are supported by the student's
   actual code or the supplied execution evidence.

5. Do NOT copy every possible misconception target into
   detected_misconceptions.

6. If there is insufficient evidence for a misconception,
   do not include it.

7. performance represents demonstrated understanding of
   the TARGET CONCEPT, from 0.0 to 1.0.

Use these approximate interpretations:

0.00 = no demonstrated understanding
0.25 = major conceptual problems
0.50 = partial understanding
0.75 = mostly correct understanding
1.00 = strong demonstrated understanding

8. confidence represents your confidence in the
   evaluation evidence, NOT the student's confidence.

9. Behavioral correctness should be strongly considered.

10. Structural requirements of the educational task
    should also be strongly considered.

Return ONLY valid JSON:

{{
    "performance": 0.0,
    "confidence": 0.0,
    "feedback": "short educational feedback",
    "detected_misconceptions": [
        "misconception supported by actual evidence"
    ]
}}
"""

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )

        raw_text = response.text.strip()

        # ==================================================
        # 5. REMOVE OPTIONAL MARKDOWN JSON FENCES
        # ==================================================

        if raw_text.startswith("```"):

            lines = raw_text.splitlines()

            if lines:
                lines = lines[1:]

            if (
                lines
                and lines[-1].strip() == "```"
            ):
                lines = lines[:-1]

            raw_text = "\n".join(
                lines
            ).strip()

            if raw_text.startswith("json"):
                raw_text = (
                    raw_text[4:].strip()
                )

        try:
            data = json.loads(
                raw_text
            )

        except json.JSONDecodeError as exc:
            raise ValueError(
                "Coding evaluator returned "
                "invalid JSON."
            ) from exc

        # ==================================================
        # 6. VALIDATE GEMINI OUTPUT
        # ==================================================

        try:
            performance = float(
                data.get(
                    "performance",
                    0.0,
                )
            )

            confidence = float(
                data.get(
                    "confidence",
                    0.0,
                )
            )

        except (
            TypeError,
            ValueError,
        ) as exc:
            raise ValueError(
                "Coding evaluator returned "
                "invalid numeric values."
            ) from exc

        performance = max(
            0.0,
            min(
                1.0,
                performance,
            ),
        )

        confidence = max(
            0.0,
            min(
                1.0,
                confidence,
            ),
        )

        feedback = str(
            data.get(
                "feedback",
                "",
            )
        ).strip()

        misconceptions = data.get(
            "detected_misconceptions",
            [],
        )

        if not isinstance(
            misconceptions,
            list,
        ):
            misconceptions = []

        misconceptions = [
            str(item).strip()
            for item in misconceptions
            if str(item).strip()
        ]

        # ==================================================
        # 7. OBJECTIVE GUARDRAILS
        # ==================================================

        # If every behavioral test failed, Gemini should
        # not be able to assign near-perfect performance.
        if (
            behavioral_result.total_count > 0
            and behavioral_result.pass_rate == 0.0
        ):
            performance = min(
                performance,
                0.50,
            )

        # If execution timed out, there is strong evidence
        # that the implementation is not behaviorally
        # correct for the supplied tests.
        if behavioral_result.timed_out:
            performance = min(
                performance,
                0.25,
            )

        # For recursion-focused tasks, if the student did
        # not use recursion, cap conceptual performance.
        #
        # This is intentionally a narrow educational
        # heuristic rather than a universal coding rule.
        if (
            "recursion"
            in task.concept_name.lower()
            and not static_result.has_recursion
        ):
            performance = min(
                performance,
                0.50,
            )

        # ==================================================
        # 8. FINAL EVALUATION
        # ==================================================

        is_correct = (
            performance >= 0.75
        )

        return CodingEvaluation(
            is_correct=is_correct,
            performance=performance,
            confidence=confidence,
            feedback=feedback,
            test_results=coding_test_results,
            detected_misconceptions=(
                misconceptions
            ),
        )