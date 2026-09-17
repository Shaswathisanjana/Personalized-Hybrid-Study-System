import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BehavioralTestCase:
    """
    One behavioral test for a student's function.

    args:
        Positional arguments passed to the function.

    expected_output:
        Expected return value OR expected printed output.

    output_mode:
        "return" -> compare function return value
        "stdout" -> compare printed output
    """

    test_name: str
    function_name: str
    args: list = field(default_factory=list)
    expected_output: object = None
    output_mode: str = "return"

    def __post_init__(self):
        if self.output_mode not in {
            "return",
            "stdout",
        }:
            raise ValueError(
                "output_mode must be 'return' or 'stdout'."
            )


@dataclass
class BehavioralTestResult:
    """
    Result produced by one behavioral test.
    """

    test_name: str
    passed: bool
    expected_output: str = ""
    actual_output: str = ""
    error: str = ""


@dataclass
class BehavioralRunResult:
    """
    Complete result of behavioral testing.
    """

    tests: list[BehavioralTestResult] = field(
        default_factory=list
    )

    timed_out: bool = False

    execution_error: str = ""

    @property
    def passed_count(self) -> int:
        return sum(
            1
            for test in self.tests
            if test.passed
        )

    @property
    def total_count(self) -> int:
        return len(self.tests)

    @property
    def pass_rate(self) -> float:
        if not self.tests:
            return 0.0

        return (
            self.passed_count
            / self.total_count
        )


class ControlledCodeRunner:
    """
    Executes student Python code in a separate
    subprocess.

    IMPORTANT:
    This is intentionally separated from the main
    application process.

    A timeout is enforced so infinite recursion or
    infinite loops do not block the main application.

    This is suitable for controlled development/testing,
    but it should NOT be treated as a complete security
    sandbox for arbitrary hostile code.
    """

    def __init__(
        self,
        timeout_seconds: float = 2.0,
    ):
        if timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds must be positive."
            )

        self.timeout_seconds = (
            timeout_seconds
        )

    def run_tests(
        self,
        code: str,
        test_cases: list[BehavioralTestCase],
    ) -> BehavioralRunResult:

        if not isinstance(code, str):
            raise TypeError(
                "code must be a string."
            )

        if not isinstance(test_cases, list):
            raise TypeError(
                "test_cases must be a list."
            )

        if not test_cases:
            return BehavioralRunResult()

        for test in test_cases:
            if not isinstance(
                test,
                BehavioralTestCase,
            ):
                raise TypeError(
                    "Every test must be a BehavioralTestCase."
                )

        # --------------------------------------------------
        # Run each test in a fresh subprocess.
        #
        # This prevents one test from contaminating the
        # state of another test.
        # --------------------------------------------------

        results = []

        for test in test_cases:
            result = self._run_single_test(
                code=code,
                test=test,
            )

            results.append(result)

            # If student code times out, there is no need
            # to continue running the same dangerous code.
            if result.error == "TIMEOUT":
                return BehavioralRunResult(
                    tests=results,
                    timed_out=True,
                    execution_error=(
                        "Student code exceeded the "
                        "execution time limit."
                    ),
                )

        return BehavioralRunResult(
            tests=results,
        )

    def _run_single_test(
        self,
        code: str,
        test: BehavioralTestCase,
    ) -> BehavioralTestResult:

        # --------------------------------------------------
        # The child script:
        #
        # 1. Loads the student's code.
        # 2. Finds the requested function.
        # 3. Calls it with predefined arguments.
        # 4. Captures printed output.
        # 5. Produces JSON for the parent process.
        #
        # Student code is executed ONLY inside the child
        # process, not inside the main application.
        # --------------------------------------------------

        student_code_json = json.dumps(code)
        function_name_json = json.dumps(
            test.function_name
        )
        args_json = json.dumps(test.args)
        output_mode_json = json.dumps(
            test.output_mode
        )

        child_script = f"""
import contextlib
import io
import json
import traceback

student_code = {student_code_json}
function_name = {function_name_json}
args = json.loads({json.dumps(args_json)})
output_mode = {output_mode_json}

namespace = {{}}

try:
    compiled_code = compile(
        student_code,
        "<student_submission>",
        "exec",
    )

    exec(
        compiled_code,
        namespace,
        namespace,
    )

    if function_name not in namespace:
        raise NameError(
            "Required function '" +
            function_name +
            "' was not found."
        )

    function = namespace[function_name]

    if not callable(function):
        raise TypeError(
            "'" +
            function_name +
            "' is not callable."
        )

    captured_output = io.StringIO()

    with contextlib.redirect_stdout(
        captured_output
    ):
        return_value = function(*args)

    stdout_value = (
        captured_output.getvalue().strip()
    )

    if output_mode == "stdout":
        actual = stdout_value

    else:
        actual = return_value

    print(
        json.dumps(
            {{
                "success": True,
                "actual": actual,
            }},
            default=str,
        )
    )

except Exception as exc:
    print(
        json.dumps(
            {{
                "success": False,
                "error": (
                    type(exc).__name__
                    + ": "
                    + str(exc)
                ),
            }}
        )
    )
"""

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                script_path = (
                    Path(temp_dir)
                    / "student_runner.py"
                )

                script_path.write_text(
                    child_script,
                    encoding="utf-8",
                )

                completed = subprocess.run(
                    [
                        sys.executable,
                        "-I",
                        str(script_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    cwd=temp_dir,
                )

        except subprocess.TimeoutExpired:
            return BehavioralTestResult(
                test_name=test.test_name,
                passed=False,
                expected_output=str(
                    test.expected_output
                ),
                actual_output="",
                error="TIMEOUT",
            )

        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()

        if not stdout:
            return BehavioralTestResult(
                test_name=test.test_name,
                passed=False,
                expected_output=str(
                    test.expected_output
                ),
                actual_output="",
                error=(
                    stderr
                    or
                    "No result was returned "
                    "by the child process."
                ),
            )

        # The final line should be the JSON produced by
        # our child runner.
        final_line = (
            stdout.splitlines()[-1]
        )

        try:
            payload = json.loads(
                final_line
            )

        except json.JSONDecodeError:
            return BehavioralTestResult(
                test_name=test.test_name,
                passed=False,
                expected_output=str(
                    test.expected_output
                ),
                actual_output=stdout,
                error=(
                    "Runner returned invalid result."
                ),
            )

        if not payload.get(
            "success",
            False,
        ):
            return BehavioralTestResult(
                test_name=test.test_name,
                passed=False,
                expected_output=str(
                    test.expected_output
                ),
                actual_output="",
                error=str(
                    payload.get(
                        "error",
                        "Unknown execution error.",
                    )
                ),
            )

        actual = payload.get(
            "actual"
        )

        expected = (
            test.expected_output
        )

        # --------------------------------------------------
        # stdout comparison
        #
        # Normalize line endings and surrounding
        # whitespace.
        # --------------------------------------------------

        if test.output_mode == "stdout":
            actual_normalized = (
                str(actual)
                .replace("\r\n", "\n")
                .strip()
            )

            expected_normalized = (
                str(expected)
                .replace("\r\n", "\n")
                .strip()
            )

            passed = (
                actual_normalized
                ==
                expected_normalized
            )

            return BehavioralTestResult(
                test_name=test.test_name,
                passed=passed,
                expected_output=(
                    expected_normalized
                ),
                actual_output=(
                    actual_normalized
                ),
            )

        # --------------------------------------------------
        # Return-value comparison
        # --------------------------------------------------

        passed = (
            actual == expected
        )

        return BehavioralTestResult(
            test_name=test.test_name,
            passed=passed,
            expected_output=str(expected),
            actual_output=str(actual),
        )