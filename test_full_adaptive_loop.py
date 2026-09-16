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

from app.learning_agent.reassessment_processor import (
    ReassessmentProcessor,
)

from app.learning_agent.agent import (
    LearningAgent,
)


# ============================================================
# 1. CREATE SHARED STUDENT MODEL
# ============================================================

student = StudentCognitiveModel(
    user_id="student_001"
)


# ============================================================
# 2. CREATE ONE SHARED COGNITIVE ENGINE
# ============================================================
#
# This SAME engine is used throughout the learning cycle.
#
# Therefore:
#
# original quiz
#       ↓
# remediation
#       ↓
# reassessment
#       ↓
# replanning
#
# all operate on the same cognitive state.
# ============================================================

engine = CognitiveEngine()


remediation_loop = RemediationLoop(
    cognitive_engine=engine
)


reassessment_processor = ReassessmentProcessor(
    cognitive_engine=engine
)


learning_agent = LearningAgent()


# ============================================================
# 3. ORIGINAL QUESTION
# ============================================================

original_question = QuizQuestion(
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


# ============================================================
# 4. ASK ORIGINAL QUESTION
# ============================================================

print(
    "\n========== ORIGINAL QUESTION =========="
)

print(
    original_question.question
)


original_answer_text = input(
    "\nEnter original answer: "
)


original_answer = StudentAnswer(
    user_id=student.user_id,

    question=original_question,

    answer=original_answer_text,
)


# ============================================================
# 5. PROCESS ORIGINAL ANSWER
# ============================================================

original_result = (
    remediation_loop.process_answer(
        student=student,
        student_answer=original_answer,
    )
)


# ============================================================
# 6. DISPLAY ORIGINAL RESULT
# ============================================================

print(
    "\n========== ORIGINAL EVALUATION =========="
)


print(
    "Correct:",
    original_result.evaluation.is_correct,
)


print(
    "Performance:",
    original_result.evaluation.performance,
)


print(
    "Detected misconceptions:",
    original_result.detected_misconceptions,
)


concept = student.get_concept(
    "Recursion"
)


print(
    "\nMastery after original answer:",
    concept.mastery,
)


print(
    "Confidence after original answer:",
    concept.confidence,
)


print(
    "Attempts:",
    concept.attempts,
)


# ============================================================
# 7. IF NO TARGETED REASSESSMENT WAS GENERATED
# ============================================================

if original_result.reassessment_question is None:

    print(
        "\nNo targeted reassessment was generated."
    )


    has_conflict = engine.has_conflict(
        user_id=student.user_id,
        concept_name="Recursion",
    )


    next_action = (
        learning_agent.choose_action(
            student=student,
            concept_name="Recursion",
            has_conflict=has_conflict,
        )
    )


    print(
        "\n========== NEXT LEARNING ACTION =========="
    )


    print(
        "Action:",
        next_action.action_type,
    )


    print(
        "Difficulty:",
        next_action.difficulty,
    )


    print(
        "Reason:",
        next_action.reason,
    )


    raise SystemExit


# ============================================================
# 8. DISPLAY REMEDIATION
# ============================================================

print(
    "\n========== REMEDIATION =========="
)


if original_result.remediation_content is not None:

    print(
        original_result.remediation_content.text
    )


# ============================================================
# 9. GET GENERATED REASSESSMENT
# ============================================================

reassessment_question = (
    original_result.reassessment_question
)


print(
    "\n========== REASSESSMENT =========="
)


print(
    reassessment_question.question
)


# ============================================================
# 10. GET TARGET MISCONCEPTION
# ============================================================

target_misconception = (
    original_result
    .detected_misconceptions[0]
)


# ============================================================
# 11. GET HYPOTHESIS BEFORE REASSESSMENT
# ============================================================

hypothesis_before = (
    engine.get_misconception_hypothesis(
        student=student,

        concept_name="Recursion",

        misconception=(
            target_misconception
        ),
    )
)


print(
    "\n========== HYPOTHESIS BEFORE REASSESSMENT =========="
)


print(
    "Description:",
    hypothesis_before.description,
)


print(
    "Confidence:",
    hypothesis_before.confidence,
)


print(
    "Supporting evidence:",
    hypothesis_before.supporting_evidence,
)


print(
    "Contradicting evidence:",
    hypothesis_before.contradicting_evidence,
)


print(
    "Status:",
    hypothesis_before.status,
)


# ============================================================
# 12. ASK STUDENT REASSESSMENT
# ============================================================

reassessment_answer_text = input(
    "\nEnter reassessment answer: "
)


reassessment_answer = StudentAnswer(
    user_id=student.user_id,

    question=reassessment_question,

    answer=reassessment_answer_text,
)


# ============================================================
# 13. PROCESS REASSESSMENT
# ============================================================

reassessment_result = (
    reassessment_processor.process(
        student=student,

        student_answer=(
            reassessment_answer
        ),

        misconception_description=(
            target_misconception
        ),
    )
)


# ============================================================
# 14. SHOW REASSESSMENT RESULT
# ============================================================

print(
    "\n========== REASSESSMENT RESULT =========="
)


print(
    "Correct:",
    reassessment_result
    .evaluation
    .is_correct,
)


print(
    "Performance:",
    reassessment_result
    .evaluation
    .performance,
)


print(
    "Feedback:",
    reassessment_result
    .evaluation
    .feedback,
)


print(
    "Same misconception detected again:",
    reassessment_result
    .misconception_detected_again,
)


# ============================================================
# 15. SHOW UPDATED HYPOTHESIS
# ============================================================

print(
    "\n========== UPDATED MISCONCEPTION HYPOTHESIS =========="
)


print(
    "Confidence:",
    reassessment_result
    .hypothesis_confidence,
)


print(
    "Supporting evidence:",
    reassessment_result
    .supporting_evidence,
)


print(
    "Contradicting evidence:",
    reassessment_result
    .contradicting_evidence,
)


print(
    "Status:",
    reassessment_result
    .hypothesis_status,
)


# ============================================================
# 16. SHOW UPDATED COGNITIVE MODEL
# ============================================================

concept = student.get_concept(
    "Recursion"
)


print(
    "\n========== UPDATED COGNITIVE STATE =========="
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
    "Active misconceptions:",
    concept.get_active_misconceptions(),
)


print(
    "Uncertain misconceptions:",
    concept.get_uncertain_misconceptions(),
)


print(
    "Resolved misconceptions:",
    concept.get_resolved_misconceptions(),
)


# ============================================================
# 17. CHECK CROSS-AGENT CONFLICT
# ============================================================

has_conflict = engine.has_conflict(
    user_id=student.user_id,

    concept_name="Recursion",
)


# ============================================================
# 18. LEARNING AGENT REPLANS
# ============================================================

next_action = (
    learning_agent.choose_action(
        student=student,

        concept_name="Recursion",

        has_conflict=has_conflict,
    )
)


print(
    "\n========== LEARNING AGENT REPLAN =========="
)


print(
    "Active cognitive conflict:",
    has_conflict,
)


print(
    "Next action:",
    next_action.action_type,
)


print(
    "Difficulty:",
    next_action.difficulty,
)


print(
    "Reason:",
    next_action.reason,
)


# ============================================================
# 19. DISPLAY EVIDENCE HISTORY
# ============================================================

history = (
    engine.evidence_store
    .get_evidence_for_concept(
        user_id=student.user_id,

        concept_name="Recursion",
    )
)


print(
    "\n========== EVIDENCE HISTORY =========="
)


for number, evidence in enumerate(
    history,
    start=1,
):

    print(
        f"\nEvidence {number}"
    )


    print(
        "Type:",
        evidence.evidence_type,
    )


    print(
        "Agent:",
        evidence.source_agent,
    )


    print(
        "Performance:",
        evidence.performance,
    )


    print(
        "Difficulty:",
        evidence.difficulty,
    )


    print(
        "Reliability:",
        evidence.reliability,
    )


    print(
        "Misconceptions:",
        evidence.detected_misconceptions,
    )


# ============================================================
# 20. FINAL SUMMARY
# ============================================================

print(
    "\n========== ADAPTIVE LOOP COMPLETE =========="
)


print(
    "Original answer processed."
)


print(
    "Misconception hypothesis processed."
)


print(
    "Targeted remediation processed."
)


print(
    "Reassessment processed."
)


print(
    "Shared cognitive state updated."
)


print(
    "Learning Agent replanned."
)