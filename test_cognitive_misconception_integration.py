from app.cognitive.models import (
    StudentCognitiveModel,
)

from app.cognitive.misconception_manager import (
    CognitiveMisconceptionManager,
)


# ==================================================
# CREATE STUDENT
# ==================================================

student = StudentCognitiveModel(
    user_id="student_001"
)

manager = CognitiveMisconceptionManager()


concept_name = "Recursion"

misconception = (
    "Confuses n-2 recursive step with n-1"
)


# ==================================================
# FIRST DETECTION
# ==================================================

hypothesis = manager.record_support(
    student=student,
    concept_name=concept_name,
    description=misconception,
    source_agent="learning",
)


concept = student.get_concept(
    concept_name
)


print(
    "\n========== FIRST DETECTION =========="
)

print(
    "Legacy misconceptions:",
    concept.misconceptions,
)

print(
    "Confidence:",
    hypothesis.confidence,
)

print(
    "Supporting:",
    hypothesis.supporting_evidence,
)

print(
    "Contradicting:",
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
# CODING AGENT ALSO OBSERVES THE SAME PROBLEM
# ==================================================

hypothesis = manager.record_support(
    student=student,
    concept_name=concept_name,
    description=misconception,
    source_agent="coding",
)


print(
    "\n========== CODING AGENT SUPPORT =========="
)

print(
    "Confidence:",
    hypothesis.confidence,
)

print(
    "Supporting:",
    hypothesis.supporting_evidence,
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
# CORRECT REASSESSMENT 1
# ==================================================

hypothesis = manager.record_contradiction(
    student=student,
    concept_name=concept_name,
    description=misconception,
    source_agent="learning",
)


print(
    "\n========== CONTRADICTION 1 =========="
)

print(
    "Confidence:",
    hypothesis.confidence,
)

print(
    "Status:",
    hypothesis.status,
)

print(
    "Legacy misconceptions:",
    concept.misconceptions,
)


# ==================================================
# CORRECT REASSESSMENT 2
# ==================================================

hypothesis = manager.record_contradiction(
    student=student,
    concept_name=concept_name,
    description=misconception,
    source_agent="learning",
)


print(
    "\n========== CONTRADICTION 2 =========="
)

print(
    "Confidence:",
    hypothesis.confidence,
)

print(
    "Status:",
    hypothesis.status,
)

print(
    "Legacy misconceptions:",
    concept.misconceptions,
)


# ==================================================
# CORRECT REASSESSMENT 3
# ==================================================

hypothesis = manager.record_contradiction(
    student=student,
    concept_name=concept_name,
    description=misconception,
    source_agent="learning",
)


print(
    "\n========== CONTRADICTION 3 =========="
)

print(
    "Confidence:",
    hypothesis.confidence,
)

print(
    "Status:",
    hypothesis.status,
)

print(
    "Legacy misconceptions:",
    concept.misconceptions,
)


# ==================================================
# FINAL COGNITIVE STATE
# ==================================================

print(
    "\n========== FINAL COGNITIVE MODEL =========="
)

print(
    "Active:",
    [
        h.description
        for h in concept.get_active_misconceptions()
    ],
)

print(
    "Uncertain:",
    [
        h.description
        for h in concept.get_uncertain_misconceptions()
    ],
)

print(
    "Resolved:",
    [
        h.description
        for h in concept.get_resolved_misconceptions()
    ],
)