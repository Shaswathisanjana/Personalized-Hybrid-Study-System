from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.evidence import LearningEvidence

from app.research_integration.evidence_adapter import (
    ResearchComprehensionResult,
    ResearchEvidenceAdapter,
)


# ============================================================
# CREATE ONE SHARED STUDENT
# ============================================================

student = StudentCognitiveModel(
    user_id="student_001"
)


# ============================================================
# CREATE ONE SHARED COGNITIVE ENGINE
# ============================================================

engine = CognitiveEngine()


# ============================================================
# STEP 1: LEARNING AGENT EVIDENCE
# ============================================================
#
# The student performs well in a Learning Agent quiz.
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


concept = student.get_concept("Recursion")


print("\n========== LEARNING AGENT ==========")

print("Source:", learning_evidence.source_agent)
print("Performance:", learning_evidence.performance)
print("Mastery:", concept.mastery)
print("Confidence:", concept.confidence)


# ============================================================
# STEP 2: RESEARCH COMPREHENSION RESULT
# ============================================================
#
# The same student now performs poorly in a research-based
# comprehension activity about the same concept.
#
# This intentionally disagrees with the Learning Agent.
# ============================================================

research_result = ResearchComprehensionResult(
    user_id="student_001",
    concept_name="Recursion",
    performance=0.20,
    difficulty=0.70,
    confidence=0.90,
)


# ============================================================
# STEP 3: CONVERT RESEARCH RESULT INTO COMMON EVIDENCE
# ============================================================

adapter = ResearchEvidenceAdapter()

research_evidence = adapter.to_learning_evidence(
    research_result
)


print("\n========== RESEARCH AGENT ==========")

print("Source:", research_evidence.source_agent)
print("Performance:", research_evidence.performance)
print("Difficulty:", research_evidence.difficulty)
print("Reliability:", research_evidence.reliability)


# ============================================================
# STEP 4: SEND RESEARCH EVIDENCE INTO SAME COGNITIVE ENGINE
# ============================================================

research_processing_result = engine.process_evidence(
    student=student,
    evidence=research_evidence,
)


print("\n========== UPDATED COGNITIVE STATE ==========")

print("Mastery:", concept.mastery)
print("Confidence:", concept.confidence)
print("Attempts:", concept.attempts)


# ============================================================
# STEP 5: CHECK WHETHER A CROSS-AGENT CONFLICT EXISTS
# ============================================================

has_conflict = engine.has_conflict(
    user_id="student_001",
    concept_name="Recursion",
)


print("\n========== CONFLICT CHECK ==========")

print(
    "Cross-agent conflict detected:",
    has_conflict
)


# ============================================================
# STEP 6: DISPLAY THE NEW CONFLICT
# ============================================================

new_conflicts = research_processing_result.get(
    "new_conflicts",
    []
)


print(
    "\nNumber of new conflicts:",
    len(new_conflicts)
)


for conflict in new_conflicts:

    print("\n---------- CONFLICT ----------")

    print(
        "Concept:",
        conflict.concept_name
    )

    print(
        "First Agent:",
        conflict.first_agent
    )

    print(
        "First Performance:",
        conflict.first_performance
    )

    print(
        "Second Agent:",
        conflict.second_agent
    )

    print(
        "Second Performance:",
        conflict.second_performance
    )

    print(
        "Difference:",
        conflict.difference
    )

    print(
        "Severity:",
        conflict.severity
    )


# ============================================================
# STEP 7: DISPLAY SHARED EVIDENCE HISTORY
# ============================================================

history = engine.evidence_store.get_evidence_for_concept(
    user_id="student_001",
    concept_name="Recursion",
)


print(
    "\n========== SHARED EVIDENCE HISTORY =========="
)


for evidence in history:

    print(
        evidence.source_agent,
        "-> performance:",
        evidence.performance,
        "| difficulty:",
        evidence.difficulty,
        "| reliability:",
        evidence.reliability,
    )


# ============================================================
# STEP 8: VERIFY EXPECTED BEHAVIOUR
# ============================================================

assert len(history) == 2

assert history[0].source_agent == "learning"
assert history[1].source_agent == "research"

assert has_conflict is True

assert len(new_conflicts) >= 1


conflict = new_conflicts[0]

assert conflict.first_agent == "learning"
assert conflict.second_agent == "research"

assert conflict.first_performance == 0.90
assert conflict.second_performance == 0.20

assert conflict.difference == 0.70

assert conflict.severity == "high"


# ============================================================
# SUCCESS
# ============================================================

print(
    "\n========== CROSS-AGENT TEST PASSED =========="
)

print(
    "Learning and Research evidence entered "
    "the same cognitive model."
)

print(
    "The CognitiveEngine automatically detected "
    "their disagreement."
)

print(
    "Conflict difference:",
    conflict.difference
)

print(
    "Conflict severity:",
    conflict.severity
)