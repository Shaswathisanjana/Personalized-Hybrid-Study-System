from app.learning_agent.quiz_models import (
    QuizQuestion,
    StudentAnswer,
)

from app.learning_agent.misconception_analyzer import (
    MisconceptionAnalyzer,
)


question = QuizQuestion(
    concept_name="Recursion",
    difficulty="medium",

    question=(
        "What is factorial(4) if factorial(1) = 1 "
        "and factorial(n) = n * factorial(n - 1)?"
    ),

    correct_answer="24",

    misconception_targets=[
        "Failure to reach the base case",
        "Off-by-one error in recursive call",
        "Incorrect understanding of recursive multiplication",
    ],
)


# Deliberately wrong answer
answer = StudentAnswer(
    user_id="student_001",
    question=question,
    answer="12",
)


analyzer = MisconceptionAnalyzer()


result = analyzer.analyze(
    answer
)


print(
    "\n========== MISCONCEPTION ANALYSIS =========="
)

print("Question:")
print(question.question)

print("\nCorrect Answer:")
print(question.correct_answer)

print("\nStudent Answer:")
print(answer.answer)

print("\nCandidate Misconceptions:")
print(question.misconception_targets)

print("\nDetected Misconceptions:")
print(result)