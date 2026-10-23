from app.cognitive.models import StudentCognitiveModel
from app.cognitive.evidence import LearningEvidence
from app.cognitive.mastery_engine import MasteryEngine


# --------------------------------------------------
# 1. CREATE STUDENT AND COGNITIVE ENGINE
# --------------------------------------------------

student = StudentCognitiveModel(user_id="student_001")
engine = MasteryEngine()


# --------------------------------------------------
# 2. INITIAL STATE
# --------------------------------------------------

recursion = student.get_concept("Recursion")

print("\n----- INITIAL COGNITIVE STATE -----")
print("Mastery:", recursion.mastery)
print("Confidence:", recursion.confidence)
print("Attempts:", recursion.attempts)


# --------------------------------------------------
# 3. LEARNING AGENT EVIDENCE
# --------------------------------------------------
#
# Imagine the student completes a recursion quiz
# and performs well.
#

learning_evidence = LearningEvidence(
    user_id="student_001",
    concept_name="Recursion",
    source_agent="learning",
    evidence_type="quiz",
    performance=0.90,
    difficulty=0.60,
    reliability=0.70
)

engine.update_from_evidence(
    student=student,
    evidence=learning_evidence
)

recursion = student.get_concept("Recursion")

print("\n----- AFTER LEARNING AGENT -----")
print("Mastery:", recursion.mastery)
print("Confidence:", recursion.confidence)
print("Attempts:", recursion.attempts)


# --------------------------------------------------
# 4. CODING AGENT EVIDENCE
# --------------------------------------------------
#
# Later, the same student attempts a difficult
# recursion coding problem but performs poorly.
#

coding_evidence = LearningEvidence(
    user_id="student_001",
    concept_name="Recursion",
    source_agent="coding",
    evidence_type="coding_solution",
    performance=0.30,
    difficulty=0.90,
    reliability=0.85
)

engine.update_from_evidence(
    student=student,
    evidence=coding_evidence
)

recursion = student.get_concept("Recursion")

print("\n----- AFTER CODING AGENT -----")
print("Mastery:", recursion.mastery)
print("Confidence:", recursion.confidence)
print("Attempts:", recursion.attempts)