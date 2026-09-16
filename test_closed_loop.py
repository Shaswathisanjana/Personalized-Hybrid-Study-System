from app.cognitive.models import StudentCognitiveModel
from app.cognitive.evidence import LearningEvidence
from app.cognitive.cognitive_engine import CognitiveEngine
from app.learning_agent.agent import LearningAgent


# ==================================================
# SETUP
# ==================================================

student = StudentCognitiveModel(user_id="student_001")

cognitive_engine = CognitiveEngine()
learning_agent = LearningAgent()


# ==================================================
# STEP 1: LEARNING AGENT QUIZ RESULT
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
    student,
    learning_evidence
)

print("\n========== AFTER LEARNING EVIDENCE ==========")

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
# STEP 2: CODING AGENT RESULT
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

coding_result = cognitive_engine.process_evidence(
    student,
    coding_evidence
)

print("\n========== AFTER CODING EVIDENCE ==========")

concept = student.get_concept("Recursion")

print("Mastery:", concept.mastery)
print("Confidence:", concept.confidence)

print(
    "New conflicts detected:",
    len(coding_result["conflicts"])
)

print(
    "Active conflict:",
    cognitive_engine.has_conflict(
        student.user_id,
        "Recursion"
    )
)


# ==================================================
# STEP 3: LEARNING AGENT READS SHARED STATE
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


print("\n========== LEARNING AGENT RE-PLANNING ==========")

print("Action:", next_action.action_type)
print("Difficulty:", next_action.difficulty)
print("Reason:", next_action.reason)


# ==================================================
# STEP 4: SHOW CONFLICT DETAILS
# ==================================================

conflicts = cognitive_engine.get_conflicts(
    student.user_id,
    "Recursion"
)

print("\n========== ACTIVE CONFLICTS ==========")

for conflict in conflicts:

    print(
        conflict.first_agent,
        "vs",
        conflict.second_agent,
        "| difference:",
        conflict.difference,
        "| severity:",
        conflict.severity
    )