from app.coding_agent.code_review_engine import CodeReviewEngine


engine = CodeReviewEngine()


def check(name, condition):
    assert condition, f"FAILED: {name}"
    print(f"PASS: {name}")


# TEST 1: Correct Python code
result = engine.review(
    "def add(a, b):\n    return a + b"
)

check(
    "Valid Python code",
    result.syntax_valid
    and result.function_names == ["add"]
    and result.has_return
    and result.issue_count == 0,
)


# TEST 2: Syntax error
result = engine.review(
    "def add(a, b)\n    return a + b"
)

check(
    "Syntax error detection",
    not result.syntax_valid
    and result.issue_count == 1
    and result.issues[0].category == "syntax_error"
    and result.issues[0].line_number == 1,
)


# TEST 3: Empty submission
result = engine.review("   ")

check(
    "Empty submission",
    not result.syntax_valid
    and result.issues[0].category == "empty_submission",
)


# TEST 4: Loop detection
result = engine.review(
    "def count(n):\n"
    "    for i in range(n):\n"
    "        print(i)"
)

check(
    "Loop detection",
    result.syntax_valid and result.has_loop,
)


# TEST 5: Recursion detection
result = engine.review(
    "def factorial(n):\n"
    "    if n <= 1:\n"
    "        return 1\n"
    "    return n * factorial(n - 1)"
)

check(
    "Recursion detection",
    result.syntax_valid and result.has_recursion,
)


# TEST 6: Invalid input type
try:
    engine.review(None)
except TypeError:
    invalid_type_rejected = True
else:
    invalid_type_rejected = False

check(
    "Invalid input type rejected",
    invalid_type_rejected,
)


print("\nALL SIX CODE REVIEW TESTS PASSED.")
