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

from app.research_agent.agent import (
    ResearchAgent,
)


USER_ID = "student_001"
CONCEPT = "recursion"


# ==========================================================
# DETERMINISTIC DIAGNOSTIC GENERATOR
#
# We use a fake generator because this test is checking
# architecture and state propagation, not Gemini quality.
# ==========================================================


class FakeDiagnosticQuizGenerator:

    def generate(
        self,
        concept_name: str,
        difficulty: str,
        mastery: float,
        confidence: float,
        quiz_type: str = "practice_quiz",
    ) -> QuizQuestion:

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


print(
    "\n=============================================="
)

print(
    "     RESEARCH STATE PROPAGATION TEST"
)

print(
    "=============================================="
)


# ==========================================================
# 1. CREATE ONE SHARED STUDENT MODEL
# ==========================================================

student = StudentCognitiveModel(
    user_id=USER_ID
)

engine = CognitiveEngine()

research_agent = ResearchAgent()


print(
    "\nStudent:",
    student.user_id,
)

print(
    "Concept:",
    CONCEPT,
)


# ==========================================================
# 2. LEARNING AGENT REPORTS STRONG PERFORMANCE
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


engine.process_evidence(
    student,
    learning_evidence,
)


state_after_learning = student.get_concept(
    CONCEPT
)


print(
    "\n========== AFTER LEARNING EVIDENCE =========="
)

print(
    "Mastery:",
    state_after_learning.mastery,
)

print(
    "Confidence:",
    state_after_learning.confidence,
)

print(
    "Conflict:",
    engine.has_conflict(
        user_id=USER_ID,
        concept_name=CONCEPT,
    ),
)


# ==========================================================
# 3. RESEARCH AGENT REPORTS CONTRADICTORY PERFORMANCE
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
        "The answer incorrectly attributes "
        "recursion difficulty only to syntax."
    ),

    detected_misconceptions=[
        (
            "Recursion difficulty is only caused "
            "by programming syntax."
        )
    ],
)


research_cacm_runtime = ResearchCACMRuntime(
    cognitive_engine=engine,
    student=student,
)


research_cacm_runtime.process_comprehension(
    user_id=USER_ID,
    question=research_question,
    evaluation=research_evaluation,
)


# ==========================================================
# 4. CHECK SHARED STATE AFTER RESEARCH EVIDENCE
# ==========================================================

state_before_resolution = student.get_concept(
    CONCEPT
)


mastery_before_resolution = (
    state_before_resolution.mastery
)

confidence_before_resolution = (
    state_before_resolution.confidence
)


has_conflict_before = engine.has_conflict(
    user_id=USER_ID,
    concept_name=CONCEPT,
)


print(
    "\n========== AFTER RESEARCH EVIDENCE =========="
)

print(
    "Mastery:",
    mastery_before_resolution,
)

print(
    "Confidence:",
    confidence_before_resolution,
)

print(
    "Conflict:",
    has_conflict_before,
)


assert (
    has_conflict_before
    is True
)


# ==========================================================
# 5. RESEARCH AGENT READS CACM STATE BEFORE RESOLUTION
#
# Because there is an active cross-agent conflict,
# Research Agent should NOT simply continue normal
# progression.
# ==========================================================

research_action_before = (
    research_agent.choose_action(
        student=student,
        concept_name=CONCEPT,
        has_active_conflict=has_conflict_before,
    )
)


print(
    "\n========== RESEARCH ACTION BEFORE RESOLUTION =========="
)

print(
    "Action:",
    research_action_before.action_type,
)

print(
    "Difficulty:",
    research_action_before.difficulty,
)

print(
    "Reason:",
    research_action_before.reason,
)


assert (
    research_action_before.action_type
    == "diagnostic_research"
)


# ==========================================================
# 6. CREATE AUTOMATIC DIAGNOSTIC INTERVENTION
# ==========================================================

diagnostic_intervention = DiagnosticIntervention(
    cognitive_engine=engine,
    quiz_generator=FakeDiagnosticQuizGenerator(),
)


cross_agent_runtime = CrossAgentRuntime(
    cognitive_engine=engine,
    diagnostic_intervention=diagnostic_intervention,
)


# ==========================================================
# 7. CACM DECIDES TO RUN DIAGNOSTIC
# ==========================================================

decision = cross_agent_runtime.decide(
    student=student,
    concept_name=CONCEPT,
)


print(
    "\n========== CACM DECISION =========="
)

print(
    "Action:",
    decision.action.action_type,
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
# 8. STUDENT ANSWERS DIAGNOSTIC CORRECTLY
# ==========================================================

session = decision.diagnostic_session


student_answer = (
    session.question.correct_answer
)


print(
    "\n========== DIAGNOSTIC =========="
)

print(
    "Question:",
    session.question.question,
)

print(
    "Student answer:",
    student_answer,
)


# ==========================================================
# 9. RESOLVE CONFLICT AND REPLAN
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


print(
    "\n========== RESOLUTION =========="
)

print(
    "Diagnostic performance:",
    diagnostic_outcome.evaluation.performance,
)

print(
    "Conflict resolved:",
    diagnostic_outcome.conflict_resolved,
)

print(
    "Has active conflict:",
    diagnostic_outcome.has_active_conflict,
)


for resolution in (
    diagnostic_outcome.resolution_results
):

    print(
        "Supported agent:",
        resolution.supported_agent,
    )

    print(
        "Reason:",
        resolution.reason,
    )


assert (
    diagnostic_outcome.conflict_resolved
    is True
)


assert (
    diagnostic_outcome.has_active_conflict
    is False
)


# ==========================================================
# 10. READ THE SAME SHARED MODEL AFTER RESOLUTION
# ==========================================================

state_after_resolution = student.get_concept(
    CONCEPT
)


mastery_after_resolution = (
    state_after_resolution.mastery
)

confidence_after_resolution = (
    state_after_resolution.confidence
)


has_conflict_after = engine.has_conflict(
    user_id=USER_ID,
    concept_name=CONCEPT,
)


print(
    "\n========== SHARED STATE AFTER RESOLUTION =========="
)

print(
    "Mastery:",
    mastery_after_resolution,
)

print(
    "Confidence:",
    confidence_after_resolution,
)

print(
    "Attempts:",
    state_after_resolution.attempts,
)

print(
    "Conflict:",
    has_conflict_after,
)


# ==========================================================
# 11. PROPAGATE UPDATED STATE TO RESEARCH AGENT
#
# IMPORTANT:
#
# We do NOT manually tell Research Agent:
# "the student improved".
#
# Research Agent reads the SAME StudentCognitiveModel
# that was updated by CACM.
# ==========================================================

research_action_after = (
    research_agent.choose_action(
        student=student,
        concept_name=CONCEPT,
        has_active_conflict=has_conflict_after,
    )
)


print(
    "\n========== RESEARCH ACTION AFTER RESOLUTION =========="
)

print(
    "Action:",
    research_action_after.action_type,
)

print(
    "Difficulty:",
    research_action_after.difficulty,
)

print(
    "Reason:",
    research_action_after.reason,
)


# ==========================================================
# 12. VALIDATE CROSS-AGENT STATE PROPAGATION
# ==========================================================


# Before resolution, Research Agent must react
# to the cross-agent conflict.
assert (
    research_action_before.action_type
    == "diagnostic_research"
)


# Conflict must disappear after diagnostic resolution.
assert (
    has_conflict_after
    is False
)


# Diagnostic success should increase mastery.
assert (
    mastery_after_resolution
    > mastery_before_resolution
)


# The Research Agent decision must change because
# the shared CACM state changed.
assert (
    research_action_after.action_type
    != research_action_before.action_type
)


# Based on our current policy:
#
# mastery >= 0.70
# confidence < 0.50
#
# should result in verification research.
assert (
    mastery_after_resolution
    >= 0.70
)


assert (
    confidence_after_resolution
    < 0.50
)


assert (
    research_action_after.action_type
    == "verification_research"
)


assert (
    research_action_after.difficulty
    == "hard"
)


# ==========================================================
# 13. SUCCESS
# ==========================================================

print(
    "\n=============================================="
)

print(
    "   CROSS-AGENT STATE PROPAGATION PASSED"
)

print(
    "=============================================="
)


print(
    "\nVerified:"
)

print(
    "1. Learning Agent contributed cognitive evidence."
)

print(
    "2. Research Agent contributed contradictory evidence."
)

print(
    "3. CACM detected cross-agent disagreement."
)

print(
    "4. Research Agent reacted to the active conflict."
)

print(
    "5. Diagnostic evidence resolved the conflict."
)

print(
    "6. CACM updated the shared cognitive state."
)

print(
    "7. Updated state propagated back to Research Agent."
)

print(
    "8. Research Agent changed its next action automatically."
)

print(
    "\nResearch action transition:"
)

print(
    research_action_before.action_type,
    "->",
    research_action_after.action_type,
)