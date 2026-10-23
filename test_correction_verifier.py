from app.coding_agent.correction_verifier import CorrectionVerifier
from app.coding_agent.code_runner import BehavioralTestCase


verifier = CorrectionVerifier()


def check(name, condition):
    assert condition, f"FAILED: {name}"
    print(f"PASS: {name}")


correct_code = (
    "def factorial(n):\n"
    "    if n <= 1:\n"
    "        return 1\n"
    "    return n * factorial(n - 1)"
)

incorrect_code = (
    "def factorial(n):\n"
    "    return n + 1"
)

syntax_error_code = (
    "def factorial(n)\n"
    "    return n"
)

test_cases = [
    BehavioralTestCase(
        test_name="Factorial of zero",
        function_name="factorial",
        args=[0],
        expected_output=1,
    ),
    BehavioralTestCase(
        test_name="Factorial of three",
        function_name="factorial",
        args=[3],
        expected_output=6,
    ),
    BehavioralTestCase(
        test_name="Factorial of five",
        function_name="factorial",
        args=[5],
        expected_output=120,
    ),
]


# TEST 1: Correct solution
result = verifier.verify(correct_code, test_cases)

check(
    "Correct solution passes supplied tests",
    result.syntax_valid
    and result.all_tests_passed
    and result.passed_count == 3
    and result.total_count == 3,
)


# TEST 2: Incorrect solution
result = verifier.verify(incorrect_code, test_cases)

check(
    "Incorrect solution is not verified",
    result.syntax_valid
    and not result.all_tests_passed
    and result.passed_count < 3,
)


# TEST 3: Syntax error
result = verifier.verify(syntax_error_code, test_cases)

check(
    "Syntax error rejected",
    not result.syntax_valid
    and not result.all_tests_passed
    and result.total_count == 0,
)


# TEST 4: No test cases
result = verifier.verify(correct_code, [])

check(
    "Missing tests leave correction unverified",
    result.syntax_valid
    and not result.all_tests_passed
    and result.total_count == 0,
)


# TEST 5: Invalid test-case input
try:
    verifier.verify(correct_code, ["not a test case"])
except TypeError:
    invalid_input_rejected = True
else:
    invalid_input_rejected = False

check(
    "Invalid test-case input rejected",
    invalid_input_rejected,
)


print("\nALL FIVE CORRECTION VERIFICATION TESTS PASSED.")
