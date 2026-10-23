from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.evidence import LearningEvidence
from app.cognitive.models import StudentCognitiveModel

from app.research_agent.models import (
    ResearchComprehensionEvaluation,
    ResearchComprehensionQuestion,
)

from app.research_agent.cacm_runtime import ResearchCACMRuntime


USER_ID = "student_001"
CONCEPT = "recursion"


# ==========================================================
# 1. CREATE SHARED CACM MODEL
# ==========================================================

student = StudentCognitiveModel(
    user_id=USER_ID
)

engine = CognitiveEngine()


print(
    "\n========== SHARED CACM MODEL CREATED =========="
)

print("Student:", student.user_id)
print("Concept:", CONCEPT)


# ==========================================================
# 2. LEARNING AGENT EVIDENCE
#
# The Learning Agent observes strong performance
# on recursion.
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


print(
    "\n========== LEARNING AGENT EVIDENCE =========="
)

print(
    "Source:",
    learning_evidence.source_agent,
)

print(
    "Performance:",
    learning_evidence.performance,
)

print(
    "Difficulty:",
    learning_evidence.difficulty,
)

print(
    "Reliability:",
    learning_evidence.reliability,
)

print(
    "Active conflict:",
    learning_result.get(
        "has_active_conflict"
    ),
)


# ==========================================================
# 3. STATE AFTER LEARNING EVIDENCE
# ==========================================================

state_after_learning = student.get_concept(
    CONCEPT
)


# Store values separately.
#
# This is important because get_concept() returns the same
# mutable ConceptState object. Later Research evidence will
# update that same object.

mastery_after_learning = (
    state_after_learning.mastery
)

confidence_after_learning = (
    state_after_learning.confidence
)

attempts_after_learning = (
    state_after_learning.attempts
)


print(
    "\n========== STATE AFTER LEARNING =========="
)

print(
    "Mastery:",
    mastery_after_learning,
)

print(
    "Confidence:",
    confidence_after_learning,
)

print(
    "Attempts:",
    attempts_after_learning,
)


# ==========================================================
# 4. RESEARCH COMPREHENSION QUESTION
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
        "The difficulty comes from mentally tracing "
        "the structure of recursive execution."
    ),

    difficulty="medium",

    misconception_targets=[
        (
            "Recursion difficulty is only caused "
            "by programming syntax."
        )
    ],
)


# ==========================================================
# 5. RESEARCH COMPREHENSION EVALUATION
#
# The semantic evaluator itself has already been tested.
#
# Here we intentionally provide a weak Research result
# so that we can test cross-agent disagreement.
# ==========================================================

research_evaluation = ResearchComprehensionEvaluation(
    is_correct=False,

    performance=0.0,

    confidence=1.0,

    feedback=(
        "The answer focuses on syntax rather than "
        "the conceptual execution structure."
    ),

    detected_misconceptions=[
        (
            "Recursion difficulty is only caused "
            "by programming syntax."
        )
    ],
)


print(
    "\n========== RESEARCH AGENT EVALUATION =========="
)

print(
    "Performance:",
    research_evaluation.performance,
)

print(
    "Confidence:",
    research_evaluation.confidence,
)

print(
    "Misconceptions:",
    research_evaluation.detected_misconceptions,
)


# ==========================================================
# 6. CONNECT RESEARCH AGENT TO CACM
#
# The SAME student model is passed to the Research runtime.
# ==========================================================

research_runtime = ResearchCACMRuntime(
    cognitive_engine=engine,
    student=student,
)


# ==========================================================
# 7. SEND RESEARCH RESULT INTO CACM
# ==========================================================

outcome = research_runtime.process_comprehension(
    user_id=USER_ID,
    question=research_question,
    evaluation=research_evaluation,
)


print(
    "\n========== RESEARCH -> CACM =========="
)

print(
    "Concept:",
    outcome.concept_name,
)

print(
    "Research performance:",
    outcome.performance,
)

print(
    "Research confidence:",
    outcome.confidence,
)

print(
    "Active conflict:",
    outcome.has_active_conflict,
)


# ==========================================================
# 8. UPDATED SHARED STATE
# ==========================================================

updated_state = student.get_concept(
    CONCEPT
)


print(
    "\n========== UPDATED SHARED STATE =========="
)

print(
    "Mastery:",
    updated_state.mastery,
)

print(
    "Confidence:",
    updated_state.confidence,
)

print(
    "Attempts:",
    updated_state.attempts,
)


# ==========================================================
# 9. INSPECT STORED EVIDENCE
# ==========================================================

learning_stored = (
    engine.evidence_store.get_evidence_from_agent(
        user_id=USER_ID,
        source_agent="learning",
    )
)


research_stored = (
    engine.evidence_store.get_evidence_from_agent(
        user_id=USER_ID,
        source_agent="research",
    )
)


print(
    "\n========== STORED LEARNING EVIDENCE =========="
)

print(
    "Count:",
    len(learning_stored),
)


for item in learning_stored:

    print(
        "Concept:",
        item.concept_name,
    )

    print(
        "Source:",
        item.source_agent,
    )

    print(
        "Performance:",
        item.performance,
    )

    print(
        "Reliability:",
        item.reliability,
    )


print(
    "\n========== STORED RESEARCH EVIDENCE =========="
)

print(
    "Count:",
    len(research_stored),
)


for item in research_stored:

    print(
        "Concept:",
        item.concept_name,
    )

    print(
        "Source:",
        item.source_agent,
    )

    print(
        "Performance:",
        item.performance,
    )

    print(
        "Difficulty:",
        item.difficulty,
    )

    print(
        "Reliability:",
        item.reliability,
    )

    print(
        "Misconceptions:",
        item.detected_misconceptions,
    )


# ==========================================================
# 10. GET CROSS-AGENT CONFLICTS
#
# Actual CognitiveEngine signature:
#
# get_conflicts(user_id, concept_name)
# ==========================================================

conflicts = engine.get_conflicts(
    user_id=USER_ID,
    concept_name=CONCEPT,
)


print(
    "\n========== COGNITIVE CONFLICTS =========="
)

print(
    "Conflict count:",
    len(conflicts),
)


# ==========================================================
# 11. DISPLAY CONFLICT DETAILS
#
# Actual CognitiveConflict fields:
#
# concept_name
# first_agent
# second_agent
# first_performance
# second_performance
# difference
# severity
# ==========================================================

for index, conflict in enumerate(
    conflicts,
    start=1,
):

    print(
        f"\nConflict {index}"
    )

    print(
        "Concept:",
        conflict.concept_name,
    )

    print(
        "First agent:",
        conflict.first_agent,
    )

    print(
        "First performance:",
        conflict.first_performance,
    )

    print(
        "Second agent:",
        conflict.second_agent,
    )

    print(
        "Second performance:",
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


# ==========================================================
# 12. VALIDATION
# ==========================================================


# ----------------------------------------------------------
# Learning evidence must be stored.
# ----------------------------------------------------------

assert (
    len(learning_stored)
    == 1
)


# ----------------------------------------------------------
# Research evidence must be stored.
# ----------------------------------------------------------

assert (
    len(research_stored)
    == 1
)


stored_research = (
    research_stored[0]
)


# ----------------------------------------------------------
# Research source identity must survive conversion.
# ----------------------------------------------------------

assert (
    stored_research.source_agent
    == "research"
)


# ----------------------------------------------------------
# Correct concept must be preserved.
# ----------------------------------------------------------

assert (
    stored_research.concept_name
    == CONCEPT
)


# ----------------------------------------------------------
# Research performance must be preserved.
# ----------------------------------------------------------

assert (
    stored_research.performance
    == 0.0
)


# ----------------------------------------------------------
# Research misconception must reach CACM.
# ----------------------------------------------------------

assert (
    len(
        stored_research.detected_misconceptions
    )
    > 0
)


assert (
    "syntax"
    in stored_research
    .detected_misconceptions[0]
    .lower()
)


# ----------------------------------------------------------
# CACM must recognize active disagreement.
# ----------------------------------------------------------

assert (
    outcome.has_active_conflict
    is True
)


# ----------------------------------------------------------
# A conflict object must have been created.
# ----------------------------------------------------------

assert (
    len(conflicts)
    > 0
)


# ----------------------------------------------------------
# Find Learning <-> Research conflict.
#
# Do not depend on conflict ordering.
# ----------------------------------------------------------

learning_research_conflict = None


for conflict in conflicts:

    agent_pair = {
        conflict.first_agent,
        conflict.second_agent,
    }

    if agent_pair == {
        "learning",
        "research",
    }:

        learning_research_conflict = (
            conflict
        )

        break


assert (
    learning_research_conflict
    is not None
)


# ----------------------------------------------------------
# Verify performances recorded in the conflict.
# ----------------------------------------------------------

performances = {
    learning_research_conflict.first_performance,
    learning_research_conflict.second_performance,
}


assert (
    performances
    == {
        0.90,
        0.0,
    }
)


# ----------------------------------------------------------
# Learning performance = 0.90
# Research performance = 0.00
#
# Difference should therefore be 0.90.
# ----------------------------------------------------------

assert (
    abs(
        learning_research_conflict.difference
        - 0.90
    )
    < 1e-9
)


# ----------------------------------------------------------
# Based on the existing conflict detector thresholds,
# this disagreement should be high severity.
# ----------------------------------------------------------

assert (
    learning_research_conflict.severity
    == "high"
)


# ----------------------------------------------------------
# SAME cognitive state received:
#
# Attempt 1 -> Learning
# Attempt 2 -> Research
# ----------------------------------------------------------

assert (
    updated_state.attempts
    == 2
)


# ----------------------------------------------------------
# Research evidence should reduce mastery because
# performance 0.0 strongly contradicts the earlier
# Learning performance 0.90.
#
# We compare against the saved numeric value rather than
# state_after_learning.mastery because ConceptState is
# mutable and represents the same shared object.
# ----------------------------------------------------------

assert (
    updated_state.mastery
    < mastery_after_learning
)


# ==========================================================
# 13. SUCCESS
# ==========================================================

print(
    "\n=============================================="
)

print(
    "       RESEARCH -> CACM TEST PASSED"
)

print(
    "=============================================="
)


print(
    "\nVerified:"
)

print(
    "1. Learning Agent evidence entered CACM."
)

print(
    "2. Research Agent evidence entered CACM."
)

print(
    "3. Both agents updated the SAME "
    "StudentCognitiveModel."
)

print(
    "4. Research misconception evidence was preserved."
)

print(
    "5. CACM detected Learning <-> Research conflict."
)

print(
    "6. Conflict magnitude and severity were preserved."
)

print(
    "7. Shared cognitive mastery adapted to "
    "contradictory Research evidence."
)