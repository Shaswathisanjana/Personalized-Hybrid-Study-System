from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.evidence import LearningEvidence

from app.cognitive.diagnostic_intervention import (
    DiagnosticIntervention,
)

from app.cognitive.cross_agent_runtime import (
    CrossAgentRuntime,
)

from app.learning_agent.quiz_models import QuizQuestion

from app.research_integration.evidence_adapter import (
    ResearchComprehensionResult,
    ResearchEvidenceAdapter,
)


# ============================================================
# FAKE DIAGNOSTIC QUIZ GENERATOR
# ============================================================
#
# We avoid Gemini in this integration test so that we are
# testing OUR architecture rather than API/network behaviour.
#
# Gemini integration can be tested separately.
# ============================================================

class FakeDiagnosticQuizGenerator:

    def generate(
        self,
        concept_name,
        difficulty,
        mastery,
        confidence,
        quiz_type="practice_quiz",
    ):

        assert quiz_type == "diagnostic_quiz"

        return QuizQuestion(
            concept_name=concept_name,
            difficulty=difficulty,
            question=(
                "In recursion, what is the condition "
                "that stops further recursive calls called?"
            ),
            correct_answer="base case",
            explanation=(
                "A base case terminates recursive calls."
            ),
            misconception_targets=[
                "Does not understand the role of a base case"
            ],
        )


# ============================================================
# CREATE SHARED SYSTEM
# ============================================================

student = StudentCognitiveModel(
    user_id="student_001"
)

engine = CognitiveEngine()


diagnostic_intervention = DiagnosticIntervention(
    cognitive_engine=engine,
    quiz_generator=FakeDiagnosticQuizGenerator(),
)


runtime = CrossAgentRuntime(
    cognitive_engine=engine,
    diagnostic_intervention=diagnostic_intervention,
)


# ============================================================
# STEP 1: LEARNING AGENT EVIDENCE
# ============================================================

learning_evidence = LearningEvidence(
    user_id="student_001",
    concept_name="Recursion",
    source_agent="learning",
    evidence_type="quiz",
    performance=0.90,
    difficulty=0.60,
    reliability=0.70,
)

engine.process_evidence(
    student=student,
    evidence=learning_evidence,
)


print("\n========== LEARNING EVIDENCE ==========")

print(
    "Performance:",
    learning_evidence.performance
)


# ============================================================
# STEP 2: RESEARCH AGENT EVIDENCE
# ============================================================

research_result = ResearchComprehensionResult(
    user_id="student_001",
    concept_name="Recursion",
    performance=0.20,
    difficulty=0.70,
    confidence=0.90,
)


research_adapter = ResearchEvidenceAdapter()

research_evidence = (
    research_adapter.to_learning_evidence(
        research_result
    )
)


research_processing = engine.process_evidence(
    student=student,
    evidence=research_evidence,
)


print("\n========== RESEARCH EVIDENCE ==========")

print(
    "Performance:",
    research_evidence.performance
)

print(
    "Reliability:",
    research_evidence.reliability
)


# ============================================================
# STEP 3: VERIFY CONFLICT
# ============================================================

assert engine.has_conflict(
    user_id="student_001",
    concept_name="Recursion",
) is True


print("\n========== CONFLICT ==========")

print(
    "New conflicts:",
    len(
        research_processing["new_conflicts"]
    )
)

conflict = research_processing[
    "new_conflicts"
][0]

print(
    "Difference:",
    conflict.difference
)

print(
    "Severity:",
    conflict.severity
)


# ============================================================
# STEP 4: CROSS-AGENT RUNTIME OBSERVES STATE
# ============================================================
#
# We DO NOT manually call DiagnosticIntervention.start().
#
# CrossAgentRuntime observes the conflict.
#
# LearningAgent should autonomously decide:
#
#     diagnostic_quiz
# ============================================================

decision = runtime.decide(
    student=student,
    concept_name="Recursion",
)


print("\n========== AGENT DECISION ==========")

print(
    "Action:",
    decision.action.action_type
)

print(
    "Difficulty:",
    decision.action.difficulty
)

print(
    "Reason:",
    decision.action.reason
)


assert (
    decision.action.action_type
    == "diagnostic_quiz"
)

assert decision.diagnostic_session is not None


# ============================================================
# STEP 5: DIAGNOSTIC GENERATED
# ============================================================

session = decision.diagnostic_session


print("\n========== DIAGNOSTIC GENERATED ==========")

print(
    "Question:",
    session.question.question
)

print(
    "Difficulty:",
    session.difficulty
)


# ============================================================
# STEP 6: STUDENT ANSWERS DIAGNOSTIC
# ============================================================
#
# No manual diagnostic performance is supplied.
#
# Student provides an actual answer.
# ============================================================

student_answer = "base case"


print("\n========== STUDENT ANSWER ==========")

print(student_answer)


# ============================================================
# STEP 7: SUBMIT + RESOLVE + AUTOMATICALLY RE-PLAN
# ============================================================

closed_loop_result = (
    runtime.submit_diagnostic_and_replan(
        student=student,
        session=session,
        answer=student_answer,
    )
)


diagnostic_outcome = (
    closed_loop_result.diagnostic_outcome
)


# ============================================================
# STEP 8: VERIFY ANSWER EVALUATION
# ============================================================

print("\n========== DIAGNOSTIC EVALUATION ==========")

print(
    "Correct:",
    diagnostic_outcome.evaluation.is_correct
)

print(
    "Performance:",
    diagnostic_outcome.evaluation.performance
)


assert (
    diagnostic_outcome.evaluation.is_correct
    is True
)

assert (
    diagnostic_outcome.evaluation.performance
    == 1.0
)


# ============================================================
# STEP 9: VERIFY CONFLICT RESOLUTION
# ============================================================

print("\n========== CONFLICT RESOLUTION ==========")

print(
    "Conflict resolved:",
    diagnostic_outcome.conflict_resolved
)

print(
    "Conflict still active:",
    diagnostic_outcome.has_active_conflict
)


assert (
    diagnostic_outcome.conflict_resolved
    is True
)

assert (
    diagnostic_outcome.has_active_conflict
    is False
)


successful_resolution = next(
    result
    for result
    in diagnostic_outcome.resolution_results
    if result.resolved
)


print(
    "Supported agent:",
    successful_resolution.supported_agent
)


assert (
    successful_resolution.supported_agent
    == "learning"
)


# ============================================================
# STEP 10: CHECK UPDATED SHARED COGNITIVE STATE
# ============================================================

concept = student.get_concept(
    "Recursion"
)


print("\n========== UPDATED COGNITIVE STATE ==========")

print(
    "Mastery:",
    concept.mastery
)

print(
    "Confidence:",
    concept.confidence
)

print(
    "Attempts:",
    concept.attempts
)


# ============================================================
# STEP 11: VERIFY AUTOMATIC RE-PLANNING
# ============================================================
#
# CrossAgentRuntime should have asked LearningAgent
# what to do NEXT after the conflict was resolved.
# ============================================================

next_action = (
    closed_loop_result.next_action
)


print("\n========== AUTOMATIC RE-PLANNING ==========")

print(
    "Next action:",
    next_action.action_type
)

print(
    "Difficulty:",
    next_action.difficulty
)

print(
    "Reason:",
    next_action.reason
)


# The conflict must no longer force another
# diagnostic quiz.

assert (
    next_action.action_type
    != "diagnostic_quiz"
)


# ============================================================
# STEP 12: VERIFY EVIDENCE HISTORY
# ============================================================

history = (
    engine.evidence_store
    .get_evidence_for_concept(
        user_id="student_001",
        concept_name="Recursion",
    )
)


print("\n========== SHARED EVIDENCE HISTORY ==========")

for evidence in history:

    print(
        evidence.source_agent,
        "|",
        evidence.evidence_type,
        "| performance:",
        evidence.performance,
        "| reliability:",
        evidence.reliability,
    )


assert len(history) == 3


# ============================================================
# FINAL SUCCESS
# ============================================================

print(
    "\n========== CROSS-AGENT CLOSED LOOP PASSED =========="
)

print(
    "1. Learning evidence entered the shared model."
)

print(
    "2. Research evidence entered the same model."
)

print(
    "3. CACM detected cross-agent disagreement."
)

print(
    "4. LearningAgent selected a diagnostic assessment."
)

print(
    "5. DiagnosticIntervention generated the assessment."
)

print(
    "6. Student response produced real diagnostic evidence."
)

print(
    "7. CognitiveEngine resolved the disagreement."
)

print(
    "8. LearningAgent automatically re-planned from "
    "the corrected shared cognitive state."
)

print(
    "Final next action:",
    next_action.action_type
)