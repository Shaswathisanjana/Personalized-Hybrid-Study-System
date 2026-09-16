from app.cognitive.models import (
    StudentCognitiveModel,
)

from app.cognitive.cognitive_engine import (
    CognitiveEngine,
)

from app.learning_agent.quiz_models import (
    QuizQuestion,
    StudentAnswer,
)

from app.learning_agent.remediation_loop import (
    RemediationLoop,
)


# ==================================================
# STUDENT
# ==================================================

student = StudentCognitiveModel(
    user_id="student_001"
)

engine = CognitiveEngine()

loop = RemediationLoop(
    cognitive_engine=engine
)


# ==================================================
# ORIGINAL QUESTION
# ==================================================

question = QuizQuestion(
    concept_name="Recursion",

    difficulty="medium",

    question=(
        "Consider the function: "
        "f(n) = 1 if n <= 0, otherwise "
        "f(n) = n * f(n - 2). "
        "What is f(4)?"
    ),

    correct_answer="8",

    explanation=(
        "f(4) = 4 * f(2), "
        "f(2) = 2 * f(0), "
        "and f(0) = 1. "
        "Therefore f(4) = 4 * 2 * 1 = 8."
    ),

    misconception_targets=[
        "Confuses n-2 recursive step with n-1"
    ],
)


# ==================================================
# STUDENT ANSWER
# ==================================================

print(
    "\n========== ORIGINAL QUESTION =========="
)

print(
    question.question
)

answer_text = input(
    "\nEnter your answer: "
)


student_answer = StudentAnswer(
    user_id="student_001",

    question=question,

    answer=answer_text,
)


# ==================================================
# RUN AUTOMATIC LOOP
# ==================================================

result = loop.process_answer(
    student=student,

    student_answer=student_answer,
)


# ==================================================
# ANSWER EVALUATION
# ==================================================

print(
    "\n========== EVALUATION =========="
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


# ==================================================
# MISCONCEPTION
# ==================================================

print(
    "\n========== MISCONCEPTION ANALYSIS =========="
)

print(
    "Detected:",
    result.detected_misconceptions,
)


# ==================================================
# COGNITIVE STATE
# ==================================================

concept = student.get_concept(
    "Recursion"
)

print(
    "\n========== COGNITIVE STATE =========="
)

print(
    "Mastery:",
    concept.mastery,
)

print(
    "Confidence:",
    concept.confidence,
)

print(
    "Attempts:",
    concept.attempts,
)

print(
    "Legacy misconceptions:",
    concept.misconceptions,
)


for description, hypothesis in (
    concept
    .misconception_hypotheses
    .items()
):

    print(
        "\nHypothesis:",
        description,
    )

    print(
        "Hypothesis confidence:",
        hypothesis.confidence,
    )

    print(
        "Supporting evidence:",
        hypothesis.supporting_evidence,
    )

    print(
        "Contradicting evidence:",
        hypothesis.contradicting_evidence,
    )

    print(
        "Status:",
        hypothesis.status,
    )

    print(
        "Sources:",
        hypothesis.source_agents,
    )


# ==================================================
# REMEDIATION
# ==================================================

if result.remediation_content is not None:

    print(
        "\n========== GROUNDED REMEDIATION =========="
    )

    print(
        result.remediation_content.text
    )


# ==================================================
# REASSESSMENT
# ==================================================

if result.reassessment_question is not None:

    print(
        "\n========== GENERATED REASSESSMENT =========="
    )

    print(
        result.reassessment_question.question
    )

    print(
        "\nCorrect answer hidden from student."
    )


else:

    print(
        "\nNo targeted reassessment was generated."
    )