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


# ============================================================
# 1. CREATE STUDENT
# ============================================================

student = StudentCognitiveModel(
    user_id="student_001"
)


# ============================================================
# 2. CREATE ONE SHARED COGNITIVE ENGINE
# ============================================================
#
# The same cognitive engine is used for:
#
# original answer
#       ↓
# misconception tracking
#       ↓
# remediation
#       ↓
# reassessment
#       ↓
# cognitive update
#       ↓
# replanning
#
# This ensures that the entire adaptive learning cycle
# operates on ONE shared student cognitive state.
# ============================================================

engine = CognitiveEngine()


# ============================================================
# 3. CREATE THE REMEDIATION ORCHESTRATOR
# ============================================================
#
# RemediationLoop now coordinates:
#
# AnswerEvaluator
# MisconceptionAnalyzer
# CognitiveEngine
# RemediationGenerator
# ReassessmentGenerator
# ReassessmentProcessor
# LearningAgent
#
# The test should therefore NOT manually create a separate
# ReassessmentProcessor or LearningAgent.
# ============================================================

remediation_loop = RemediationLoop(
    cognitive_engine=engine
)


# ============================================================
# 4. ORIGINAL QUESTION
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
# 5. ASK ORIGINAL QUESTION
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
# 6. PROCESS ORIGINAL ANSWER
# ============================================================
#
# RemediationLoop now handles:
#
# evaluation
#     ↓
# misconception analysis
#     ↓
# cognitive evidence
#     ↓
# misconception hypothesis
#     ↓
# remediation
#     ↓
# reassessment generation
#
# ============================================================

original_result = (
    remediation_loop.process_answer(
        student=student,

        student_answer=original_answer,
    )
)


# ============================================================
# 7. DISPLAY ORIGINAL RESULT
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
# 8. HANDLE CASE WHERE NO REASSESSMENT IS NEEDED
# ============================================================

if original_result.reassessment_question is None:

    print(
        "\nNo targeted reassessment was generated."
    )


    next_action = (
        remediation_loop.get_next_action(
            student=student,

            concept_name="Recursion",
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


    print(
        "\n========== ADAPTIVE LOOP COMPLETE =========="
    )


    raise SystemExit


# ============================================================
# 9. DISPLAY REMEDIATION
# ============================================================

print(
    "\n========== GROUNDED REMEDIATION =========="
)


if original_result.remediation_content is not None:

    print(
        original_result.remediation_content.text
    )


# ============================================================
# 10. GET GENERATED REASSESSMENT
# ============================================================

reassessment_question = (
    original_result.reassessment_question
)


print(
    "\n========== VALIDATED REASSESSMENT =========="
)


print(
    reassessment_question.question
)


print(
    "\nValidated correct answer stored internally:",
    reassessment_question.correct_answer,
)


# ============================================================
# 11. GET TARGET MISCONCEPTION
# ============================================================

target_misconception = (
    original_result
    .detected_misconceptions[0]
)


# ============================================================
# 12. DISPLAY HYPOTHESIS BEFORE REASSESSMENT
# ============================================================

hypothesis_before = (
    engine.get_misconception_hypothesis(
        student=student,

        concept_name="Recursion",

        misconception=target_misconception,
    )
)


print(
    "\n========== HYPOTHESIS BEFORE REASSESSMENT =========="
)


if hypothesis_before is not None:

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
# 13. ASK REASSESSMENT
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
# 14. PROCESS REASSESSMENT THROUGH REMEDIATION LOOP
# ============================================================
#
# THIS IS THE IMPORTANT ARCHITECTURAL CHANGE.
#
# Previously this test manually called:
#
# ReassessmentProcessor.process(...)
#
# and then manually called:
#
# LearningAgent.choose_action(...)
#
#
# Now ONE orchestrator performs:
#
# reassessment
#      ↓
# evaluation
#      ↓
# evidence update
#      ↓
# misconception update
#      ↓
# conflict check
#      ↓
# Learning Agent replan
#
# ============================================================

adaptive_result = (
    remediation_loop.process_reassessment(
        student=student,

        student_answer=reassessment_answer,

        misconception_description=(
            target_misconception
        ),
    )
)


# ============================================================
# 15. GET INNER REASSESSMENT RESULT
# ============================================================

reassessment_result = (
    adaptive_result.reassessment_result
)


# ============================================================
# 16. SHOW REASSESSMENT RESULT
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
# 17. SHOW UPDATED MISCONCEPTION HYPOTHESIS
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
# 18. SHOW COGNITIVE STATE RETURNED BY ORCHESTRATOR
# ============================================================

print(
    "\n========== UPDATED COGNITIVE STATE =========="
)


print(
    "Mastery:",
    adaptive_result.mastery,
)


print(
    "Confidence:",
    adaptive_result.confidence,
)


print(
    "Attempts:",
    adaptive_result.attempts,
)


concept = student.get_concept(
    "Recursion"
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
# 19. SHOW CONFLICT STATE
# ============================================================

print(
    "\n========== COGNITIVE CONFLICT =========="
)


print(
    "Active cognitive conflict:",
    adaptive_result.has_active_conflict,
)


# ============================================================
# 20. SHOW AUTOMATIC LEARNING AGENT REPLAN
# ============================================================

next_action = (
    adaptive_result.next_action
)


print(
    "\n========== AUTOMATIC LEARNING AGENT REPLAN =========="
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
# 21. DISPLAY EVIDENCE HISTORY
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
# 22. BASIC INTEGRATION ASSERTIONS
# ============================================================
#
# These assertions make this more than a visual demo.
#
# They prove that:
#
# 1. the reassessment became cognitive evidence
# 2. the student model was updated
# 3. the Learning Agent produced another action
#
# ============================================================

assert concept.attempts >= 2


assert len(history) >= 2


assert adaptive_result.next_action is not None


assert (
    adaptive_result.mastery
    == concept.mastery
)


assert (
    adaptive_result.confidence
    == concept.confidence
)


# ============================================================
# 23. FINAL SUMMARY
# ============================================================

print(
    "\n========== FULL ADAPTIVE LOOP VERIFIED =========="
)


print(
    "Original answer processed."
)


print(
    "Misconception hypothesis updated."
)


print(
    "Grounded remediation generated."
)


print(
    "Reassessment deterministically validated."
)


print(
    "Reassessment processed through shared orchestrator."
)


print(
    "Shared cognitive state updated."
)


print(
    "Conflict state checked."
)


print(
    "Learning Agent automatically replanned."
)


print(
    "\nFULL LEARNING AGENT CLOSED LOOP PASSED."
)