from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.evidence import LearningEvidence

from app.research_integration.evidence_adapter import (
    ResearchComprehensionResult,
    ResearchEvidenceAdapter,
)


# ============================================================
# CREATE SHARED STUDENT AND COGNITIVE ENGINE
# ============================================================

student = StudentCognitiveModel(
    user_id="student_001"
)

engine = CognitiveEngine()


# ============================================================
# STEP 1: LEARNING AGENT EVIDENCE
# ============================================================
#
# Learning Agent observes strong performance.
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

print("Agent:", learning_evidence.source_agent)
print("Performance:", learning_evidence.performance)


# ============================================================
# STEP 2: RESEARCH AGENT EVIDENCE
# ============================================================
#
# Research-based comprehension gives a very different result.
# ============================================================

research_result = ResearchComprehensionResult(
    user_id="student_001",
    concept_name="Recursion",
    performance=0.20,
    difficulty=0.70,
    confidence=0.90,
)

adapter = ResearchEvidenceAdapter()

research_evidence = adapter.to_learning_evidence(
    research_result
)

research_processing = engine.process_evidence(
    student=student,
    evidence=research_evidence,
)

print("\n========== RESEARCH EVIDENCE ==========")

print("Agent:", research_evidence.source_agent)
print("Performance:", research_evidence.performance)


# ============================================================
# STEP 3: VERIFY CROSS-AGENT CONFLICT
# ============================================================

new_conflicts = research_processing[
    "new_conflicts"
]

assert len(new_conflicts) >= 1

conflict = new_conflicts[0]

print("\n========== CONFLICT DETECTED ==========")

print("Concept:", conflict.concept_name)

print(
    "First Agent:",
    conflict.first_agent,
    "->",
    conflict.first_performance,
)

print(
    "Second Agent:",
    conflict.second_agent,
    "->",
    conflict.second_performance,
)

print("Difference:", conflict.difference)
print("Severity:", conflict.severity)


conflict_before = engine.has_conflict(
    user_id="student_001",
    concept_name="Recursion",
)

print(
    "Conflict active before diagnostic:",
    conflict_before
)

assert conflict_before is True


# ============================================================
# STEP 4: DIAGNOSTIC INTERVENTION
# ============================================================
#
# CACM does not blindly choose Learning or Research.
#
# A diagnostic assessment is used to obtain stronger
# evidence about the student's actual understanding.
#
# Diagnostic = 0.25
#
# Distance from Learning:
# |0.25 - 0.90| = 0.65
#
# Distance from Research:
# |0.25 - 0.20| = 0.05
#
# Therefore the diagnostic supports Research.
# ============================================================

diagnostic_evidence = LearningEvidence(
    user_id="student_001",
    concept_name="Recursion",
    source_agent="learning",
    evidence_type="diagnostic_quiz",
    performance=0.25,
    difficulty=0.80,
    reliability=0.90,
)

print("\n========== DIAGNOSTIC INTERVENTION ==========")

print(
    "Performance:",
    diagnostic_evidence.performance
)

print(
    "Difficulty:",
    diagnostic_evidence.difficulty
)

print(
    "Reliability:",
    diagnostic_evidence.reliability
)


# ============================================================
# STEP 5: PROCESS DIAGNOSTIC THROUGH COGNITIVE ENGINE
# ============================================================

diagnostic_processing = engine.process_evidence(
    student=student,
    evidence=diagnostic_evidence,
)


# ============================================================
# STEP 6: READ ACTUAL RESOLUTION RESULTS
# ============================================================
#
# IMPORTANT:
#
# CognitiveEngine returns:
#
#     "resolution_results"
#
# not:
#
#     "resolutions"
# ============================================================

resolution_results = diagnostic_processing[
    "resolution_results"
]


print("\n========== RESOLUTION RESULT ==========")

print(
    "Number of resolutions:",
    len(resolution_results)
)


for resolution in resolution_results:

    print("\nConcept:", resolution.concept_name)

    print(
        "Resolved:",
        resolution.resolved
    )

    print(
        "Supported Agent:",
        resolution.supported_agent
    )

    print(
        "Diagnostic Performance:",
        resolution.diagnostic_performance
    )

    print(
        "Distance from Learning Evidence:",
        resolution.first_distance
    )

    print(
        "Distance from Research Evidence:",
        resolution.second_distance
    )

    print(
        "Reason:",
        resolution.reason
    )


# ============================================================
# STEP 7: VERIFY RESOLUTION
# ============================================================

assert len(resolution_results) >= 1

successful_resolutions = [
    resolution
    for resolution in resolution_results
    if resolution.resolved
]

assert len(successful_resolutions) >= 1

successful_resolution = successful_resolutions[0]


# Diagnostic should support Research.

assert (
    successful_resolution.supported_agent
    == "research"
)


# Expected distances:
#
# Learning:
# |0.25 - 0.90| = 0.65
#
# Research:
# |0.25 - 0.20| = 0.05

assert (
    successful_resolution.first_distance
    == 0.65
)

assert (
    successful_resolution.second_distance
    == 0.05
)


# ============================================================
# STEP 8: CHECK ENGINE'S RESOLUTION SUMMARY
# ============================================================

print("\n========== ENGINE RESOLUTION SUMMARY ==========")

print(
    "Conflict resolved:",
    diagnostic_processing[
        "conflict_resolved"
    ]
)

print(
    "Has active conflict:",
    diagnostic_processing[
        "has_active_conflict"
    ]
)


assert (
    diagnostic_processing[
        "conflict_resolved"
    ]
    is True
)

assert (
    diagnostic_processing[
        "has_active_conflict"
    ]
    is False
)


# ============================================================
# STEP 9: VERIFY DIRECT ENGINE STATE
# ============================================================

conflict_after = engine.has_conflict(
    user_id="student_001",
    concept_name="Recursion",
)


print("\n========== FINAL CONFLICT STATE ==========")

print(
    "Conflict active after diagnostic:",
    conflict_after
)

assert conflict_after is False


# ============================================================
# STEP 10: FINAL COGNITIVE STATE
# ============================================================

concept = student.get_concept(
    "Recursion"
)


print("\n========== FINAL COGNITIVE STATE ==========")

print("Mastery:", concept.mastery)
print("Confidence:", concept.confidence)
print("Attempts:", concept.attempts)


# ============================================================
# STEP 11: EVIDENCE HISTORY
# ============================================================

history = (
    engine.evidence_store
    .get_evidence_for_concept(
        user_id="student_001",
        concept_name="Recursion",
    )
)


print("\n========== EVIDENCE HISTORY ==========")


for evidence in history:

    print(
        evidence.source_agent,
        "|",
        evidence.evidence_type,
        "| performance:",
        evidence.performance,
        "| difficulty:",
        evidence.difficulty,
        "| reliability:",
        evidence.reliability,
    )


assert len(history) == 3


# ============================================================
# SUCCESS
# ============================================================

print(
    "\n========== CROSS-AGENT CONFLICT RESOLUTION PASSED =========="
)

print(
    "Learning and Research produced conflicting "
    "evidence about Recursion."
)

print(
    "CACM detected the disagreement."
)

print(
    "Diagnostic evidence was collected."
)

print(
    "Diagnostic evidence supported:",
    successful_resolution.supported_agent
)

print(
    "The original cross-agent conflict "
    "was successfully resolved."
)