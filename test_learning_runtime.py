from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine
from app.learning_agent.runtime import LearningAgentRuntime


# ==================================================
# SETUP
# ==================================================

student = StudentCognitiveModel(
    user_id="student_001"
)

engine = CognitiveEngine()

runtime = LearningAgentRuntime(
    cognitive_engine=engine
)


# ==================================================
# STEP 1: SET INITIAL COGNITIVE STATE
# ==================================================

concept = student.get_concept("Recursion")

concept.mastery = 0.30
concept.confidence = 0.20

print("\n========== INITIAL STATE ==========")

print("Concept:", concept.concept_name)
print("Mastery:", concept.mastery)
print("Confidence:", concept.confidence)


# ==================================================
# STEP 2: ASK AGENT FOR NEXT ACTIVITY
# ==================================================

activity = runtime.get_next_activity(
    student=student,
    concept_name="Recursion",
)

print("\n========== AGENT ACTIVITY ==========")

print("Activity Type:", activity.activity_type)
print("Difficulty:", activity.difficulty)
print("Content:", activity.content)
print(
    "Requires Response:",
    activity.requires_response
)


# ==================================================
# STEP 3: SIMULATE STUDENT PERFORMANCE
# ==================================================

print("\n========== STUDENT PERFORMANCE ==========")

performance = 0.75

print("Performance:", performance)


# ==================================================
# STEP 4: SUBMIT RESULT + AUTOMATIC RE-PLANNING
# ==================================================

result = runtime.submit_and_replan(
    student=student,
    concept_name="Recursion",
    performance=performance,
    evidence_type="quiz",
    difficulty=0.50,
    reliability=0.70,
)

cognitive_result = result["cognitive_result"]

updated_concept = cognitive_result["concept"]

next_activity = result["next_activity"]


# ==================================================
# STEP 5: SHOW UPDATED COGNITIVE STATE
# ==================================================

print("\n========== UPDATED COGNITIVE STATE ==========")

print(
    "Mastery:",
    updated_concept.mastery
)

print(
    "Confidence:",
    updated_concept.confidence
)

print(
    "Attempts:",
    updated_concept.attempts
)


# ==================================================
# STEP 6: SHOW AUTOMATIC RE-PLANNING
# ==================================================

print("\n========== AUTOMATIC RE-PLANNING ==========")

print(
    "Next Activity:",
    next_activity.activity_type
)

print(
    "Difficulty:",
    next_activity.difficulty
)

print(
    "Content:",
    next_activity.content
)

print(
    "Requires Response:",
    next_activity.requires_response
)