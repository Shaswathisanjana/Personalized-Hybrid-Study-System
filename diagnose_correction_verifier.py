from app.coding_agent.correction_verifier import CorrectionVerifier
from app.coding_agent.code_runner import BehavioralTestCase

code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""

tests = [
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

verifier = CorrectionVerifier()

for attempt in range(1, 4):
    result = verifier.verify(code, tests)

    print(f"\n========== ATTEMPT {attempt} ==========")
    print("Syntax valid:", result.syntax_valid)
    print("All tests passed:", result.all_tests_passed)
    print("Passed count:", result.passed_count)
    print("Total count:", result.total_count)
    print("Timed out:", result.timed_out)
    print("Execution error:", repr(result.execution_error))
    print("Message:", result.message)

    for test in result.test_results:
        print(
            "Test:", test.test_name,
            "| Passed:", test.passed,
            "| Expected:", repr(test.expected_output),
            "| Actual:", repr(test.actual_output),
            "| Error:", repr(test.error),
        )
