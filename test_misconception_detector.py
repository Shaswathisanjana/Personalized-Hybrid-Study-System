from app.coding_agent.models import CodingTask
from app.coding_agent.misconception_detector import CodingMisconceptionDetector


detector = CodingMisconceptionDetector()


def make_task(concept):
    return CodingTask(
        concept_name=concept,
        title=f"{concept} Practice",
        description=f"Practice {concept}.",
        difficulty="easy",
    )


def check(concept, code, expected_codes, label):
    result = detector.analyze(make_task(concept), code)
    actual_codes = {finding.code for finding in result.findings}

    assert result.syntax_valid, f"{label}: Unexpected syntax error"
    assert actual_codes == set(expected_codes), (
        f"{label}: Expected {set(expected_codes)}, got {actual_codes}"
    )

    print(f"PASS: {label}")

    for finding in result.findings:
        print(f"      Detected: {finding.code}")
        print(f"      Hint: {finding.targeted_hint}")


# 1. Recursive function with no visible conditional.
check(
    "Recursion",
    "def factorial(n):\n    return n * factorial(n - 1)\n",
    {"possible_missing_base_case"},
    "Missing recursion base case",
)

# 2. Recursive call passes the same argument.
check(
    "Recursion",
    "def factorial(n):\n    if n == 0:\n        return 1\n    return factorial(n)\n",
    {"unchanged_recursive_argument"},
    "Unchanged recursive argument",
)

# 3. Correct recursive structure.
check(
    "Recursion",
    "def factorial(n):\n    if n == 0:\n        return 1\n    return n * factorial(n - 1)\n",
    set(),
    "Correct recursion not flagged",
)

# 4. Incorrect prime-number edge case.
check(
    "Prime Numbers",
    "def is_prime(n):\n    if n == 1:\n        return True\n    return False\n",
    {"one_marked_as_prime"},
    "One incorrectly marked as prime",
)

# 5. Correct prime-number edge case.
check(
    "Prime Numbers",
    "def is_prime(n):\n    if n < 2:\n        return False\n    return True\n",
    set(),
    "Correct prime-number edge case not flagged",
)

# 6. Potentially incorrect maximum initialization.
check(
    "Arrays",
    "def find_max(nums):\n    maximum = 0\n    for n in nums:\n        if n > maximum:\n            maximum = n\n    return maximum\n",
    {"zero_initialized_maximum"},
    "Zero-initialized maximum",
)

# 7. Correct maximum initialization.
check(
    "Arrays",
    "def find_max(nums):\n    maximum = nums[0]\n    for n in nums:\n        if n > maximum:\n            maximum = n\n    return maximum\n",
    set(),
    "Correct array maximum not flagged",
)

# 8. Invalid syntax must be reported safely.
invalid = detector.analyze(
    make_task("Recursion"),
    "def factorial(:\n    pass\n",
)

assert invalid.syntax_valid is False
assert invalid.findings == []
print("PASS: Invalid syntax handled safely")

# 9. Empty code must not produce a fabricated misconception.
empty = detector.analyze(make_task("Recursion"), "")

assert empty.findings == []
print("PASS: Empty code produces no misconception")

print()
print("ALL MISCONCEPTION DETECTOR TESTS PASSED")
