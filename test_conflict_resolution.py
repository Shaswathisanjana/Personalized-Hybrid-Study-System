from app.cognitive.models import StudentCognitiveModel
from app.cognitive.evidence import LearningEvidence
from app.cognitive.cognitive_engine import CognitiveEngine
from app.learning_agent.agent import LearningAgent


# ==================================================
# SETUP
# ==================================================

student = StudentCognitiveModel(
    user_id="student_001"
)

cognitive_engine = CognitiveEngine()
learning_agent = LearningAgent()


# ==================================================
# STEP 1: LEARNING AGENT EVIDENCE
# Student performs well in a quiz
# ==================================================

learning_evidence = LearningEvidence(
    user_id="student_001",
    concept_name="Recursion",
    source_agent="learning",
    evidence_type="quiz",
    performance=0.90,
    difficulty=0.60,
    reliability=0.70
)

cognitive_engine.process_evidence(
    student=student,
    evidence=learning_evidence
)

print("\n========== STEP 1: LEARNING EVIDENCE ==========")

concept = student.get_concept("Recursion")

print("Mastery:", concept.mastery)
print("Confidence:", concept.confidence)

print(
    "Active conflict:",
    cognitive_engine.has_conflict(
        student.user_id,
        "Recursion"
    )
)


# ==================================================
# STEP 2: CODING AGENT EVIDENCE
# Student performs poorly in coding
# ==================================================

coding_evidence = LearningEvidence(
    user_id="student_001",
    concept_name="Recursion",
    source_agent="coding",
    evidence_type="coding_solution",
    performance=0.30,
    difficulty=0.90,
    reliability=0.85
)

cognitive_engine.process_evidence(
    student=student,
    evidence=coding_evidence
)

print("\n========== STEP 2: CODING EVIDENCE ==========")

concept = student.get_concept("Recursion")

print("Mastery:", concept.mastery)
print("Confidence:", concept.confidence)

print(
    "Active conflict:",
    cognitive_engine.has_conflict(
        student.user_id,
        "Recursion"
    )
)


# ==================================================
# STEP 3: LEARNING AGENT RE-PLANS
# ==================================================

has_conflict = cognitive_engine.has_conflict(
    student.user_id,
    "Recursion"
)

action = learning_agent.choose_action(
    student=student,
    concept_name="Recursion",
    has_conflict=has_conflict
)

print("\n========== STEP 3: AGENT RE-PLANNING ==========")

print("Action:", action.action_type)
print("Difficulty:", action.difficulty)
print("Reason:", action.reason)


# ==================================================
# STEP 4: STUDENT TAKES DIAGNOSTIC QUIZ
#
# For this test we simulate a diagnostic score of 0.55.
# ==================================================

diagnostic_evidence = LearningEvidence(
    user_id="student_001",
    concept_name="Recursion",
    source_agent="learning",
    evidence_type="diagnostic_quiz",
    performance=0.55,
    difficulty=0.70,
    reliability=0.80
)

diagnostic_result = cognitive_engine.process_evidence(
    student=student,
    evidence=diagnostic_evidence
)

print("\n========== STEP 4: DIAGNOSTIC RESULT ==========")

concept = student.get_concept("Recursion")

print("Diagnostic performance:", diagnostic_evidence.performance)

print("Mastery:", concept.mastery)
print("Confidence:", concept.confidence)

print(
    "Conflict resolved:",
    diagnostic_result["conflict_resolved"]
)

print(
    "Active conflict:",
    cognitive_engine.has_conflict(
        student.user_id,
        "Recursion"
    )
)


# ==================================================
# STEP 5: LEARNING AGENT RE-PLANS AGAIN
# ==================================================

has_conflict = cognitive_engine.has_conflict(
    student.user_id,
    "Recursion"
)

next_action = learning_agent.choose_action(
    student=student,
    concept_name="Recursion",
    has_conflict=has_conflict
)

print("\n========== STEP 5: FINAL RE-PLANNING ==========")

print("Action:", next_action.action_type)
print("Difficulty:", next_action.difficulty)
print("Reason:", next_action.reason)


# ==================================================
# STEP 6: FINAL COGNITIVE STATE
# ==================================================

concept = student.get_concept("Recursion")

print("\n========== FINAL COGNITIVE STATE ==========")

print("Concept:", concept.concept_name)
print("Mastery:", concept.mastery)
print("Confidence:", concept.confidence)
print("Attempts:", concept.attempts)