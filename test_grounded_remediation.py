from app.cognitive.models import (
    StudentCognitiveModel,
)

from app.learning_agent.quiz_models import (
    QuizQuestion,
    StudentAnswer,
)

from app.learning_agent.remediation import (
    create_remediation_context,
)

from app.learning_agent.remediation_generator import (
    RemediationGenerator,
)

from app.learning_agent.gemini_provider import (
    GeminiContentProvider,
)


# ==================================================
# STUDENT COGNITIVE STATE
# ==================================================

student = StudentCognitiveModel(
    user_id="student_001"
)

concept = student.get_concept(
    "Recursion"
)

concept.mastery = 0.257
concept.confidence = 0.302
concept.attempts = 1


# ==================================================
# ORIGINAL QUESTION
# ==================================================

question = QuizQuestion(
    concept_name="Recursion",

    difficulty="medium",

    question=(
        "Consider the following function: "
        "function f(n) { "
        "if (n <= 1) return 1; "
        "return n * f(n - 2); "
        "} "
        "What is the result of f(4)?"
    ),

    correct_answer="8",

    explanation=(
        "f(4) = 4 * f(2), "
        "f(2) = 2 * f(0), "
        "and f(0) = 1. "
        "Therefore f(4) = 4 * 2 * 1 = 8."
    ),

    misconception_targets=[
        (
            "Incorrectly reducing the recursive "
            "step value"
        )
    ],
)


# ==================================================
# STUDENT'S WRONG ANSWER
# ==================================================

student_answer = StudentAnswer(
    user_id=student.user_id,
    question=question,
    answer="3",
)


# ==================================================
# MISCONCEPTION HYPOTHESIS
# ==================================================

detected_misconceptions = [
    (
        "Incorrectly reducing the recursive step "
        "value by confusing n-2 with n-1"
    )
]


# ==================================================
# CREATE GROUNDED REMEDIATION CONTEXT
# ==================================================

context = create_remediation_context(
    student_answer=student_answer,
    detected_misconceptions=(
        detected_misconceptions
    ),
)


# ==================================================
# BUILD REMEDIATION REQUEST
# ==================================================

generator = RemediationGenerator()

request = generator.generate(
    student=student,
    context=context,
)


print(
    "\n========== ORIGINAL QUESTION =========="
)

print(
    context.original_question
)


print(
    "\n========== STUDENT ANSWER =========="
)

print(
    context.student_answer
)


print(
    "\n========== CORRECT ANSWER =========="
)

print(
    context.correct_answer
)


print(
    "\n========== MISCONCEPTION HYPOTHESIS =========="
)

print(
    context.detected_misconceptions
)


# ==================================================
# GEMINI
# ==================================================

provider = GeminiContentProvider()

lesson = provider.create_content(
    request
)


print(
    "\n========== GROUNDED REMEDIATION =========="
)

print(
    lesson
)