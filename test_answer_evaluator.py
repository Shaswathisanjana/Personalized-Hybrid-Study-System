from app.learning_agent.quiz_models import (
    QuizQuestion,
    StudentAnswer,
)

from app.learning_agent.answer_evaluator import (
    AnswerEvaluator,
)


question = QuizQuestion(
    concept_name="Recursion",
    difficulty="medium",
    question="What is mystery(5)?",
    correct_answer="9",
    misconception_targets=[
        "incorrect recursive tracing"
    ],
)


evaluator = AnswerEvaluator()


# =====================================
# TEST CORRECT ANSWER
# =====================================

correct_response = StudentAnswer(
    user_id="student_001",
    question=question,
    answer="9",
)

correct_result = evaluator.evaluate(
    correct_response
)

print("\n===== CORRECT ANSWER TEST =====")

print(
    "Correct:",
    correct_result.is_correct
)

print(
    "Performance:",
    correct_result.performance
)

print(
    "Feedback:",
    correct_result.feedback
)


# =====================================
# TEST WRONG ANSWER
# =====================================

wrong_response = StudentAnswer(
    user_id="student_001",
    question=question,
    answer="8",
)

wrong_result = evaluator.evaluate(
    wrong_response
)

print("\n===== WRONG ANSWER TEST =====")

print(
    "Correct:",
    wrong_result.is_correct
)

print(
    "Performance:",
    wrong_result.performance
)

print(
    "Feedback:",
    wrong_result.feedback
)

print(
    "Misconceptions:",
    wrong_result.detected_misconceptions
)