from app.learning_agent.reassessment_generator import (
    ReassessmentGenerator,
)


# We deliberately bypass __init__ here because this
# unit test only tests our deterministic validator.
validator = object.__new__(
    ReassessmentGenerator
)


# ============================================================
# TEST 1
# Previously broken additive question
# ============================================================

question_1 = (
    "Consider the function: "
    "g(n) = 2 if n <= 1, otherwise "
    "g(n) = g(n - 2) + 3. "
    "What is g(5)?"
)


result_1 = (
    validator._validate_generated_answer(
        question_text=question_1,

        # Deliberately give the WRONG Gemini answer
        generated_answer="11",
    )
)


print(
    "========== ADDITIVE TEST =========="
)

print(
    "Validated:",
    result_1["validated"],
)

print(
    "Correct answer:",
    result_1["correct_answer"],
)


assert (
    result_1["validated"]
    is True
)

assert (
    result_1["correct_answer"]
    == 8
)


# ============================================================
# TEST 2
# Multiplicative question
# ============================================================

question_2 = (
    "Consider the function: "
    "g(n) = 2 if n <= 1, otherwise "
    "g(n) = 3 * g(n - 2). "
    "What is g(5)?"
)


result_2 = (
    validator._validate_generated_answer(
        question_text=question_2,

        generated_answer="18",
    )
)


print(
    "\n========== MULTIPLICATIVE TEST =========="
)

print(
    "Validated:",
    result_2["validated"],
)

print(
    "Correct answer:",
    result_2["correct_answer"],
)


assert (
    result_2["validated"]
    is True
)

assert (
    result_2["correct_answer"]
    == 18
)


print(
    "\n========== VALIDATION TESTS PASSED =========="
)