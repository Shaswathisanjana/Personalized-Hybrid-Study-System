from app.coding_agent.verified_exercises import get_verified_exercise
from app.coding_agent.code_runner import ControlledCodeRunner

solutions = {
    "Recursion": """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
""",
    "Prime Numbers": """
def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True
""",
    "Arrays": """
def find_max(nums):
    largest = nums[0]
    for value in nums[1:]:
        if value > largest:
            largest = value
    return largest
""",
}

runner = ControlledCodeRunner(timeout_seconds=5.0)

for concept, solution in solutions.items():
    exercise = get_verified_exercise(concept)

    result = runner.run_tests(
        code=solution,
        test_cases=exercise.test_cases,
    )

    print(
        f"{concept}: "
        f"{result.passed_count}/{result.total_count} passed"
    )

    for test in result.tests:
        if not test.passed:
            print(
                f"  FAILED: {test.test_name} "
                f"Error: {test.error}"
            )

    assert result.total_count == len(exercise.test_cases)
    assert result.passed_count == result.total_count
    assert not result.timed_out
    assert not result.execution_error

print("\nALL VERIFIED EXERCISE TESTS PASSED.")
