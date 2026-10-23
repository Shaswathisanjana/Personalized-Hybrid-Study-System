from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.evidence import LearningEvidence
from app.cognitive.diagnostic_intervention import (
    DiagnosticIntervention,
)

from app.learning_agent.quiz_models import QuizQuestion

from app.research_integration.evidence_adapter import (
    ResearchComprehensionResult,
    ResearchEvidenceAdapter,
)


# ============================================================
# FAKE QUIZ GENERATOR
# ============================================================
#
# We intentionally avoid Gemini in this test.
#
# Why?
# We want to test our CACM diagnostic pipeline independently
# from network/API/model availability.
#
# The real GeminiQuizGenerator will be tested separately.
# ============================================================

class FakeQuizGenerator:

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
                "In recursion, what is the name of the "
                "condition that stops further recursive calls?"
            ),
            correct_answer="base case",
            explanation=(
                "A base case terminates the recursive process."
            ),
            misconception_targets=[
                "Does not understand the role of a base case"
            ],
        )


# ============================================================
# CREATE SHARED COGNITIVE SYSTEM
# ============================================================

student = StudentCognitiveModel(
    user_id="student_001"
)

engine = CognitiveEngine()


# ============================================================
# STEP 1: LEARNING AGENT SAYS PERFORMANCE IS HIGH
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


# ============================================================
# STEP 2: RESEARCH AGENT SAYS PERFORMANCE IS LOW
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


print("\n========== CROSS-AGENT EVIDENCE ==========")

print(
    "Learning performance:",
    learning_evidence.performance
)

print(
    "Research performance:",
    research_evidence.performance
)

print(
    "New conflicts:",
    len(
        research_processing["new_conflicts"]
    )
)


# ============================================================
# STEP 3: VERIFY CONFLICT EXISTS
# ============================================================

assert engine.has_conflict(
    user_id="student_001",
    concept_name="Recursion",
) is True


print("\nConflict detected successfully.")


# ============================================================
# STEP 4: CREATE AUTOMATIC DIAGNOSTIC INTERVENTION
# ============================================================

diagnostic = DiagnosticIntervention(
    cognitive_engine=engine,
    quiz_generator=FakeQuizGenerator(),
)


# ============================================================
# STEP 5: SYSTEM STARTS DIAGNOSTIC
# ============================================================

session = diagnostic.start(
    student=student,
    concept_name="Recursion",
)


print("\n========== AUTOMATIC DIAGNOSTIC ==========")

print(
    "Concept:",
    session.concept_name
)

print(
    "Difficulty:",
    session.difficulty
)

print(
    "Question:",
    session.question.question
)


assert (
    session.question.question_type
    == "short_answer"
)


# ============================================================
# STEP 6: STUDENT ANSWERS
# ============================================================
#
# This is the important difference from our previous test.
#
# We do NOT manually set:
#
#     performance = 0.25
#
# The student provides an answer.
#
# AnswerEvaluator converts that answer into performance.
# ============================================================

student_response = "base case"


outcome = diagnostic.submit_answer(
    student=student,
    session=session,
    answer=student_response,
)


# ============================================================
# STEP 7: CHECK REAL EVALUATION
# ============================================================

print("\n========== ANSWER EVALUATION ==========")

print(
    "Student answer:",
    student_response
)

print(
    "Correct:",
    outcome.evaluation.is_correct
)

print(
    "Performance:",
    outcome.evaluation.performance
)


assert outcome.evaluation.is_correct is True

assert outcome.evaluation.performance == 1.0


# ============================================================
# STEP 8: CHECK GENERATED DIAGNOSTIC EVIDENCE
# ============================================================

print("\n========== DIAGNOSTIC EVIDENCE ==========")

print(
    "Source agent:",
    outcome.evidence.source_agent
)

print(
    "Evidence type:",
    outcome.evidence.evidence_type
)

print(
    "Performance:",
    outcome.evidence.performance
)

print(
    "Difficulty:",
    outcome.evidence.difficulty
)

print(
    "Reliability:",
    outcome.evidence.reliability
)


assert (
    outcome.evidence.evidence_type
    == "diagnostic_quiz"
)

assert (
    outcome.evidence.performance
    == outcome.evaluation.performance
)


# ============================================================
# STEP 9: CHECK CONFLICT RESOLUTION
# ============================================================

print("\n========== CONFLICT RESOLUTION ==========")

print(
    "Resolution results:",
    len(outcome.resolution_results)
)

for resolution in outcome.resolution_results:

    print(
        "Resolved:",
        resolution.resolved
    )

    print(
        "Supported agent:",
        resolution.supported_agent
    )

    print(
        "Diagnostic performance:",
        resolution.diagnostic_performance
    )

    print(
        "Reason:",
        resolution.reason
    )


assert len(outcome.resolution_results) >= 1

assert outcome.conflict_resolved is True

assert outcome.has_active_conflict is False


# ============================================================
# STEP 10: VERIFY WHICH AGENT WAS SUPPORTED
# ============================================================
#
# Diagnostic performance = 1.0
#
# Learning evidence = 0.90
# Research evidence = 0.20
#
# Therefore the diagnostic should support Learning.
# ============================================================

successful_resolution = next(
    result
    for result in outcome.resolution_results
    if result.resolved
)


assert (
    successful_resolution.supported_agent
    == "learning"
)


# ============================================================
# STEP 11: VERIFY SHARED EVIDENCE HISTORY
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
    )


assert len(history) == 3


# ============================================================
# SUCCESS
# ============================================================

print(
    "\n========== AUTOMATIC DIAGNOSTIC TEST PASSED =========="
)

print(
    "Learning and Research produced conflicting evidence."
)

print(
    "CACM automatically required a diagnostic activity."
)

print(
    "The student answered the diagnostic question."
)

print(
    "AnswerEvaluator produced the diagnostic performance."
)

print(
    "CognitiveEngine used that evidence to resolve "
    "the cross-agent conflict."
)

print(
    "Supported agent:",
    successful_resolution.supported_agent
)