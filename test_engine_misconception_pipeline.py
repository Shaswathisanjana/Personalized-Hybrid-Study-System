from app.cognitive.models import (
    StudentCognitiveModel,
)

from app.cognitive.evidence import (
    LearningEvidence,
)

from app.cognitive.cognitive_engine import (
    CognitiveEngine,
)


student = StudentCognitiveModel(
    user_id="student_001"
)

engine = CognitiveEngine()

misconception = (
    "Confuses n-2 recursive step with n-1"
)


# ==================================================
# LEARNING AGENT EVIDENCE
# ==================================================

learning_evidence = LearningEvidence(
    user_id="student_001",

    concept_name="Recursion",

    source_agent="learning",

    evidence_type="quiz",

    performance=0.0,

    difficulty=0.5,

    reliability=0.7,

    detected_misconceptions=[
        misconception
    ],
)


result = engine.process_evidence(
    student=student,
    evidence=learning_evidence,
)


hypothesis = (
    engine.get_misconception_hypothesis(
        student=student,
        concept_name="Recursion",
        misconception=misconception,
    )
)


print(
    "\n========== AFTER LEARNING AGENT =========="
)

print(
    "Mastery:",
    student.get_concept("Recursion").mastery,
)

print(
    "Hypothesis confidence:",
    hypothesis.confidence,
)

print(
    "Supporting evidence:",
    hypothesis.supporting_evidence,
)

print(
    "Sources:",
    hypothesis.source_agents,
)

print(
    "Status:",
    hypothesis.status,
)


# ==================================================
# CODING AGENT EVIDENCE
# ==================================================

coding_evidence = LearningEvidence(
    user_id="student_001",

    concept_name="Recursion",

    source_agent="coding",

    evidence_type="coding_solution",

    performance=0.2,

    difficulty=0.8,

    reliability=0.8,

    detected_misconceptions=[
        misconception
    ],
)


engine.process_evidence(
    student=student,
    evidence=coding_evidence,
)


print(
    "\n========== AFTER CODING AGENT =========="
)

print(
    "Mastery:",
    student.get_concept("Recursion").mastery,
)

print(
    "Hypothesis confidence:",
    hypothesis.confidence,
)

print(
    "Supporting evidence:",
    hypothesis.supporting_evidence,
)

print(
    "Sources:",
    hypothesis.source_agents,
)

print(
    "Status:",
    hypothesis.status,
)


# ==================================================
# CORRECT REASSESSMENT
# ==================================================

engine.record_misconception_contradiction(
    student=student,

    concept_name="Recursion",

    misconception=misconception,

    source_agent="learning",
)


print(
    "\n========== AFTER CORRECT REASSESSMENT =========="
)

print(
    "Hypothesis confidence:",
    hypothesis.confidence,
)

print(
    "Supporting evidence:",
    hypothesis.supporting_evidence,
)

print(
    "Contradicting evidence:",
    hypothesis.contradicting_evidence,
)

print(
    "Status:",
    hypothesis.status,
)


# ==================================================
# SHARED COGNITIVE STATE
# ==================================================

concept = student.get_concept(
    "Recursion"
)


print(
    "\n========== SHARED COGNITIVE MODEL =========="
)

print(
    "Legacy misconceptions:",
    concept.misconceptions,
)

print(
    "Structured hypotheses:",
    list(
        concept.misconception_hypotheses.keys()
    ),
)

print(
    "Active hypotheses:",
    [
        h.description
        for h in concept.get_active_misconceptions()
    ],
)