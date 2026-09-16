from app.learning_agent.quiz_models import (
    QuizQuestion,
    StudentAnswer,
)

from app.cognitive.misconception_tracker import (
    MisconceptionTracker,
)

from app.learning_agent.reassessment_processor import (
    ReassessmentProcessor,
)


# ==============================================
# MISCONCEPTION HYPOTHESIS
# ==============================================

misconception = (
    "Confuses n-2 recursive step with n-1"
)

tracker = MisconceptionTracker()

hypothesis = tracker.create_hypothesis(
    description=misconception,
    source_agent="learning",
)


# ==============================================
# REASSESSMENT QUESTION
# ==============================================

question = QuizQuestion(
    concept_name="Recursion",

    difficulty="easy",

    question=(
        "Consider the function: "
        "g(n) = 1 if n <= 0, otherwise "
        "g(n) = n * g(n - 2). "
        "What is g(5)?"
    ),

    correct_answer="15",

    explanation=(
        "g(5) = 5 * g(3), "
        "g(3) = 3 * g(1), "
        "g(1) = 1 * g(-1), "
        "and g(-1) = 1. "
        "Therefore g(5) = 15."
    ),

    misconception_targets=[
        misconception
    ],
)


print(
    "\n========== REASSESSMENT =========="
)

print(
    question.question
)

print(
    "\nCorrect answer is hidden from student."
)


# ==============================================
# STUDENT ANSWER
# ==============================================

answer = input(
    "\nEnter your answer: "
)


student_answer = StudentAnswer(
    user_id="student_001",
    question=question,
    answer=answer,
)


# ==============================================
# PROCESS ANSWER
# ==============================================

processor = ReassessmentProcessor()

result = processor.process(
    student_answer=student_answer,
    hypothesis=hypothesis,
)


# ==============================================
# OUTPUT
# ==============================================

print(
    "\n========== ANSWER EVALUATION =========="
)

print(
    "Correct:",
    result.evaluation.is_correct,
)

print(
    "Performance:",
    result.evaluation.performance,
)

print(
    "Feedback:",
    result.evaluation.feedback,
)


print(
    "\n========== MISCONCEPTION EVIDENCE =========="
)

print(
    "Detected again:",
    result.misconception_detected_again,
)

print(
    "Supporting evidence:",
    result.supporting_evidence,
)

print(
    "Contradicting evidence:",
    result.contradicting_evidence,
)


print(
    "\n========== UPDATED HYPOTHESIS =========="
)

print(
    "Confidence:",
    result.hypothesis_confidence,
)

print(
    "Status:",
    result.hypothesis_status,
)