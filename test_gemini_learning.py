from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine

from app.learning_agent.runtime import LearningAgentRuntime
from app.learning_agent.gemini_provider import GeminiContentProvider


# ==========================================
# SETUP
# ==========================================

student = StudentCognitiveModel(
    user_id="student_001"
)

engine = CognitiveEngine()

gemini_provider = GeminiContentProvider()

runtime = LearningAgentRuntime(
    cognitive_engine=engine,
    content_provider=gemini_provider,
)


# ==========================================
# INITIAL COGNITIVE STATE
# ==========================================

concept = student.get_concept("Recursion")

concept.mastery = 0.30
concept.confidence = 0.20


print("\n========== COGNITIVE STATE ==========")

print("Concept:", concept.concept_name)
print("Mastery:", concept.mastery)
print("Confidence:", concept.confidence)


# ==========================================
# GEMINI PERSONALIZED LESSON
# ==========================================

activity = runtime.get_next_activity(
    student=student,
    concept_name="Recursion",
)

print("\n========== GEMINI ACTIVITY ==========")

print("Activity Type:", activity.activity_type)
print("Difficulty:", activity.difficulty)

print("\nGenerated Content:\n")
print(activity.content)


# ==========================================
# SIMULATED STUDENT RESULT
# ==========================================

result = runtime.submit_and_replan(
    student=student,
    concept_name="Recursion",
    performance=0.75,
    evidence_type="quiz",
    difficulty=0.50,
    reliability=0.70,
)

updated_concept = (
    result["cognitive_result"]["concept"]
)

next_activity = result["next_activity"]


print("\n========== COGNITIVE UPDATE ==========")

print(
    "Updated Mastery:",
    updated_concept.mastery
)

print(
    "Updated Confidence:",
    updated_concept.confidence
)


print("\n========== GEMINI RE-PLANNING ==========")

print(
    "Next Activity:",
    next_activity.activity_type
)

print(
    "Difficulty:",
    next_activity.difficulty
)

print("\nGenerated Content:\n")

print(
    next_activity.content
)