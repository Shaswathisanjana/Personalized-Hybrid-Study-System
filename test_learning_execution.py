from app.cognitive.models import StudentCognitiveModel
from app.cognitive.evidence import LearningEvidence
from app.cognitive.cognitive_engine import CognitiveEngine

from app.learning_agent.agent import LearningAgent
from app.learning_agent.executor import LearningActionExecutor


# ==================================================
# SETUP
# ==================================================

student = StudentCognitiveModel(
    user_id="student_001"
)

cognitive_engine = CognitiveEngine()
learning_agent = LearningAgent()
executor = LearningActionExecutor()


# ==================================================
# STEP 1: INITIAL STUDENT STATE
# ==================================================

concept = student.get_concept("Recursion")

# For this test, assume the student initially
# has weak understanding of recursion.
concept.mastery = 0.30
concept.confidence = 0.20

print("\n========== INITIAL STUDENT STATE ==========")

print("Concept:", concept.concept_name)
print("Mastery:", concept.mastery)
print("Confidence:", concept.confidence)


# ==================================================
# STEP 2: LEARNING AGENT OBSERVES STATE
# ==================================================

has_conflict = cognitive_engine.has_conflict(
    student.user_id,
    "Recursion"
)

action = learning_agent.choose_action(
    student=student,
    concept_name="Recursion",
    has_conflict=has_conflict,
)

print("\n========== LEARNING AGENT DECISION ==========")

print("Action:", action.action_type)
print("Difficulty:", action.difficulty)
print("Reason:", action.reason)


# ==================================================
# STEP 3: EXECUTE THE ACTION
# ==================================================

activity = executor.execute(action)

print("\n========== EXECUTED LEARNING ACTIVITY ==========")

print("Activity Type:", activity.activity_type)
print("Concept:", activity.concept_name)
print("Difficulty:", activity.difficulty)
print("Content:", activity.content)
print("Requires Response:", activity.requires_response)


# ==================================================
# STEP 4: SIMULATE STUDENT LEARNING + QUIZ
#
# Later this will come from the real UI.
# For now, assume the student completes the lesson
# and then scores 75% on a quiz.
# ==================================================

quiz_score = 0.75

learning_evidence = LearningEvidence(
    user_id=student.user_id,
    concept_name="Recursion",
    source_agent="learning",
    evidence_type="quiz",
    performance=quiz_score,
    difficulty=0.50,
    reliability=0.70,
)


# ==================================================
# STEP 5: SEND RESULT TO COGNITIVE ENGINE
# ==================================================

result = cognitive_engine.process_evidence(
    student=student,
    evidence=learning_evidence,
)

updated_concept = result["concept"]

print("\n========== COGNITIVE UPDATE ==========")

print("Quiz Performance:", quiz_score)
print("Updated Mastery:", updated_concept.mastery)
print("Updated Confidence:", updated_concept.confidence)
print("Attempts:", updated_concept.attempts)


# ==================================================
# STEP 6: LEARNING AGENT OBSERVES AGAIN
# ==================================================

has_conflict = cognitive_engine.has_conflict(
    student.user_id,
    "Recursion"
)

next_action = learning_agent.choose_action(
    student=student,
    concept_name="Recursion",
    has_conflict=has_conflict,
)

print("\n========== LEARNING AGENT RE-PLANNING ==========")

print("Next Action:", next_action.action_type)
print("Difficulty:", next_action.difficulty)
print("Reason:", next_action.reason)


# ==================================================
# STEP 7: EXECUTE THE NEW ACTION
# ==================================================

next_activity = executor.execute(
    next_action
)

print("\n========== NEXT LEARNING ACTIVITY ==========")

print("Activity Type:", next_activity.activity_type)
print("Concept:", next_activity.concept_name)
print("Difficulty:", next_activity.difficulty)
print("Content:", next_activity.content)
print(
    "Requires Response:",
    next_activity.requires_response
)