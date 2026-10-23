from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.models import StudentCognitiveModel
from app.cognitive.evidence import LearningEvidence

from app.cognitive.diagnostic_intervention import (
    DiagnosticIntervention,
)

from app.cognitive.cross_agent_runtime import (
    CrossAgentRuntime,
)

from app.learning_agent.quiz_models import (
    QuizQuestion,
)

from app.research_agent.models import (
    ResearchComprehensionQuestion,
    ResearchComprehensionEvaluation,
)

from app.research_agent.cacm_runtime import (
    ResearchCACMRuntime,
)


USER_ID = "student_001"
CONCEPT = "recursion"


# ==========================================================
# FAKE DIAGNOSTIC QUIZ GENERATOR
#
# We deliberately make the diagnostic deterministic.
#
# We are NOT testing Gemini here.
# We are testing the CACM architecture:
#
# conflict
#    ↓
# diagnostic
#    ↓
# resolution
#    ↓
# re-planning
# ==========================================================


class FakeDiagnosticQuizGenerator:
    """
    Deterministic diagnostic generator used only for testing.

    It follows the same interface as GeminiQuizGenerator,
    but avoids Gemini variability during the architecture test.
    """

    def generate(
        self,
        concept_name: str,
        difficulty: str,
        mastery: float,
        confidence: float,
        quiz_type: str = "practice_quiz",
    ) -> QuizQuestion:

        print(
            "\n[FakeDiagnosticQuizGenerator]"
        )

        print(
            "Generating diagnostic for:",
            concept_name,
        )

        print(
            "Difficulty:",
            difficulty,
        )

        print(
            "Current mastery:",
            mastery,
        )

        print(
            "Current confidence:",
            confidence,
        )

        print(
            "Quiz type:",
            quiz_type,
        )

        return QuizQuestion(
            concept_name=concept_name,

            difficulty=difficulty,

            question=(
                "What is the purpose of a base case "
                "in recursion?"
            ),

            question_type="short_answer",

            correct_answer=(
                "It stops the recursive calls."
            ),

            explanation=(
                "A base case provides the stopping "
                "condition for recursion."
            ),

            misconception_targets=[
                (
                    "Recursion does not require "
                    "a stopping condition."
                )
            ],
        )


# ==========================================================
# 1. CREATE SHARED STUDENT MODEL
# ==========================================================

student = StudentCognitiveModel(
    user_id=USER_ID
)

engine = CognitiveEngine()


print(
    "\n=============================================="
)

print(
    "     CROSS-AGENT RESOLUTION TEST"
)

print(
    "=============================================="
)

print(
    "\nStudent:",
    student.user_id,
)

print(
    "Concept:",
    CONCEPT,
)


# ==========================================================
# 2. LEARNING AGENT PRODUCES STRONG EVIDENCE
# ==========================================================

learning_evidence = LearningEvidence(
    user_id=USER_ID,
    concept_name=CONCEPT,
    source_agent="learning",
    evidence_type="practice_quiz",
    performance=0.90,
    difficulty=0.60,
    reliability=0.90,
    detected_misconceptions=[],
)


learning_result = engine.process_evidence(
    student,
    learning_evidence,
)


learning_state = student.get_concept(
    CONCEPT
)


mastery_after_learning = (
    learning_state.mastery
)


print(
    "\n========== LEARNING EVIDENCE =========="
)

print(
    "Performance:",
    learning_evidence.performance,
)

print(
    "Mastery after Learning:",
    mastery_after_learning,
)

print(
    "Conflict:",
    learning_result.get(
        "has_active_conflict"
    ),
)


# ==========================================================
# 3. CREATE RESEARCH COMPREHENSION RESULT
#
# Research evidence strongly contradicts Learning.
# ==========================================================

research_question = ResearchComprehensionQuestion(
    concept_name=CONCEPT,

    question=(
        "Why can recursion be difficult for "
        "novice programmers?"
    ),

    correct_answer=(
        "Recursion requires students to trace "
        "non-linear and hierarchical execution."
    ),

    explanation=(
        "Students must mentally follow nested "
        "recursive execution."
    ),

    difficulty="medium",

    misconception_targets=[
        (
            "Recursion difficulty is only caused "
            "by programming syntax."
        )
    ],
)


research_evaluation = ResearchComprehensionEvaluation(
    is_correct=False,

    performance=0.0,

    confidence=1.0,

    feedback=(
        "The answer incorrectly attributes the "
        "difficulty only to syntax."
    ),

    detected_misconceptions=[
        (
            "Recursion difficulty is only caused "
            "by programming syntax."
        )
    ],
)


# ==========================================================
# 4. SEND RESEARCH EVIDENCE INTO SAME CACM MODEL
# ==========================================================

research_runtime = ResearchCACMRuntime(
    cognitive_engine=engine,
    student=student,
)


research_outcome = (
    research_runtime.process_comprehension(
        user_id=USER_ID,
        question=research_question,
        evaluation=research_evaluation,
    )
)


state_after_research = student.get_concept(
    CONCEPT
)


mastery_after_research = (
    state_after_research.mastery
)


print(
    "\n========== RESEARCH EVIDENCE =========="
)

print(
    "Performance:",
    research_evaluation.performance,
)

print(
    "Mastery after Research:",
    mastery_after_research,
)

print(
    "Active conflict:",
    research_outcome.has_active_conflict,
)


# ==========================================================
# 5. VERIFY CONFLICT EXISTS BEFORE INTERVENTION
# ==========================================================

conflicts_before = engine.get_conflicts(
    user_id=USER_ID,
    concept_name=CONCEPT,
)


print(
    "\n========== CONFLICT BEFORE DIAGNOSTIC =========="
)

print(
    "Conflict count:",
    len(conflicts_before),
)


for conflict in conflicts_before:

    print(
        "Agents:",
        conflict.first_agent,
        "<->",
        conflict.second_agent,
    )

    print(
        "Performances:",
        conflict.first_performance,
        "<->",
        conflict.second_performance,
    )

    print(
        "Difference:",
        conflict.difference,
    )

    print(
        "Severity:",
        conflict.severity,
    )


assert (
    len(conflicts_before)
    > 0
)


assert (
    research_outcome.has_active_conflict
    is True
)


# ==========================================================
# 6. CREATE DIAGNOSTIC INTERVENTION
#
# Uses:
#   - real CognitiveEngine
#   - fake deterministic quiz generator
#   - real AnswerEvaluator by default
# ==========================================================

diagnostic_intervention = (
    DiagnosticIntervention(
        cognitive_engine=engine,
        quiz_generator=FakeDiagnosticQuizGenerator(),
    )
)


# ==========================================================
# 7. CREATE CROSS-AGENT RUNTIME
# ==========================================================

cross_agent_runtime = CrossAgentRuntime(
    cognitive_engine=engine,
    diagnostic_intervention=diagnostic_intervention,
)


# ==========================================================
# 8. ASK CACM WHAT TO DO
#
# Because Learning and Research disagree,
# the expected action is diagnostic_quiz.
# ==========================================================

decision = cross_agent_runtime.decide(
    student=student,
    concept_name=CONCEPT,
)


print(
    "\n========== CROSS-AGENT DECISION =========="
)

print(
    "Action:",
    decision.action.action_type,
)

print(
    "Concept:",
    decision.action.concept_name,
)

print(
    "Difficulty:",
    decision.action.difficulty,
)

print(
    "Reason:",
    decision.action.reason,
)


assert (
    decision.action.action_type
    == "diagnostic_quiz"
)


assert (
    decision.diagnostic_session
    is not None
)


# ==========================================================
# 9. DISPLAY AUTOMATIC DIAGNOSTIC
# ==========================================================

session = decision.diagnostic_session


print(
    "\n========== DIAGNOSTIC SESSION =========="
)

print(
    "Student:",
    session.user_id,
)

print(
    "Concept:",
    session.concept_name,
)

print(
    "Difficulty:",
    session.difficulty,
)

print(
    "Question:",
    session.question.question,
)

print(
    "Expected answer:",
    session.question.correct_answer,
)


# ==========================================================
# 10. STUDENT ANSWERS DIAGNOSTIC
#
# The answer intentionally supports the earlier
# Learning Agent evidence.
#
# AnswerEvaluator performs exact matching in the
# current implementation, so we use the exact
# expected answer.
# ==========================================================

student_answer = (
    session.question.correct_answer
)


print(
    "\n========== STUDENT DIAGNOSTIC ANSWER =========="
)

print(
    student_answer
)


# ==========================================================
# 11. SUBMIT DIAGNOSTIC + AUTOMATICALLY REPLAN
# ==========================================================

resolution_outcome = (
    cross_agent_runtime
    .submit_diagnostic_and_replan(
        student=student,
        session=session,
        answer=student_answer,
    )
)


diagnostic_outcome = (
    resolution_outcome.diagnostic_outcome
)


# ==========================================================
# 12. DISPLAY DIAGNOSTIC EVALUATION
# ==========================================================

print(
    "\n========== DIAGNOSTIC EVALUATION =========="
)

print(
    "Correct:",
    diagnostic_outcome.evaluation.is_correct,
)

print(
    "Performance:",
    diagnostic_outcome.evaluation.performance,
)

print(
    "Feedback:",
    diagnostic_outcome.evaluation.feedback,
)

print(
    "Conflict resolved:",
    diagnostic_outcome.conflict_resolved,
)

print(
    "Has active conflict:",
    diagnostic_outcome.has_active_conflict,
)


# ==========================================================
# 13. DISPLAY CONFLICT RESOLUTION
# ==========================================================

print(
    "\n========== CONFLICT RESOLUTION =========="
)


for resolution in (
    diagnostic_outcome.resolution_results
):

    print(
        "Concept:",
        resolution.concept_name,
    )

    print(
        "Resolved:",
        resolution.resolved,
    )

    print(
        "Supported agent:",
        resolution.supported_agent,
    )

    print(
        "Diagnostic performance:",
        resolution.diagnostic_performance,
    )

    print(
        "Distance from first agent:",
        resolution.first_distance,
    )

    print(
        "Distance from second agent:",
        resolution.second_distance,
    )

    print(
        "Reason:",
        resolution.reason,
    )


# ==========================================================
# 14. CHECK SHARED STATE AFTER DIAGNOSTIC
# ==========================================================

final_state = student.get_concept(
    CONCEPT
)


print(
    "\n========== SHARED STATE AFTER DIAGNOSTIC =========="
)

print(
    "Mastery:",
    final_state.mastery,
)

print(
    "Confidence:",
    final_state.confidence,
)

print(
    "Attempts:",
    final_state.attempts,
)


# ==========================================================
# 15. AUTOMATIC RE-PLANNING
#
# CrossAgentRuntime should ask the Learning Agent
# for the next action AFTER diagnostic evidence has
# updated the cognitive state.
# ==========================================================

next_action = (
    resolution_outcome.next_action
)


print(
    "\n========== AUTOMATIC RE-PLANNING =========="
)

print(
    "Next action:",
    next_action.action_type,
)

print(
    "Concept:",
    next_action.concept_name,
)

print(
    "Difficulty:",
    next_action.difficulty,
)

print(
    "Reason:",
    next_action.reason,
)


# ==========================================================
# 16. FINAL VALIDATION
# ==========================================================


# Learning and Research must initially disagree.
assert (
    len(conflicts_before)
    > 0
)


# CACM must automatically select diagnostic intervention.
assert (
    decision.action.action_type
    == "diagnostic_quiz"
)


# Diagnostic must be answered correctly.
assert (
    diagnostic_outcome.evaluation.is_correct
    is True
)


assert (
    diagnostic_outcome.evaluation.performance
    == 1.0
)


# At least one resolution result should exist.
assert (
    len(
        diagnostic_outcome.resolution_results
    )
    > 0
)


# Find successful resolution.
successful_resolution = None


for resolution in (
    diagnostic_outcome.resolution_results
):

    if resolution.resolved:

        successful_resolution = (
            resolution
        )

        break


assert (
    successful_resolution
    is not None
)


# Diagnostic score 1.0 is much closer to
# Learning performance 0.90 than Research 0.00.
assert (
    successful_resolution.supported_agent
    == "learning"
)


# Conflict should have been resolved.
assert (
    diagnostic_outcome.conflict_resolved
    is True
)


assert (
    diagnostic_outcome.has_active_conflict
    is False
)


# Three cognitive observations:
#
# 1. Learning
# 2. Research
# 3. Diagnostic
assert (
    final_state.attempts
    == 3
)


# Diagnostic success should increase mastery relative
# to the weak state produced after Research evidence.
assert (
    final_state.mastery
    > mastery_after_research
)


# After successful resolution, the system should no
# longer immediately request another diagnostic.
assert (
    next_action.action_type
    != "diagnostic_quiz"
)


# ==========================================================
# 17. SUCCESS
# ==========================================================

print(
    "\n=============================================="
)

print(
    "   FULL CROSS-AGENT LOOP TEST PASSED"
)

print(
    "=============================================="
)


print(
    "\nVerified:"
)

print(
    "1. Learning Agent reported strong mastery."
)

print(
    "2. Research Agent reported weak mastery."
)

print(
    "3. CACM detected cross-agent conflict."
)

print(
    "4. Conflict automatically triggered diagnostic."
)

print(
    "5. Student diagnostic evidence was evaluated."
)

print(
    "6. CACM resolved which agent was better supported."
)

print(
    "7. Shared cognitive state was updated."
)

print(
    "8. System automatically selected the next action."
)