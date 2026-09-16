from app.learning_agent.reassessment_generator import (
    ReassessmentGenerator,
)


concept_name = "Recursion"

misconception = (
    "Incorrectly reducing the recursive step value "
    "by confusing n-2 with n-1"
)

previous_question = (
    "Consider the following function: "
    "function f(n) { "
    "if (n <= 1) return 1; "
    "return n * f(n - 2); "
    "} "
    "What is the result of f(4)?"
)


print(
    "\n========== PREVIOUS QUESTION =========="
)

print(
    previous_question
)


print(
    "\n========== MISCONCEPTION BEING TESTED =========="
)

print(
    misconception
)


generator = ReassessmentGenerator()


question = generator.generate(
    concept_name=concept_name,
    misconception=misconception,
    previous_question=previous_question,
)


print(
    "\n========== NEW REASSESSMENT QUESTION =========="
)

print(
    question.question
)


print(
    "\n========== CORRECT ANSWER =========="
)

print(
    question.correct_answer
)


print(
    "\n========== EXPLANATION =========="
)

print(
    question.explanation
)


print(
    "\n========== MISCONCEPTION TARGET =========="
)

print(
    question.misconception_targets
)