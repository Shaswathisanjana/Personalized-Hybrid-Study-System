from app.cognitive.models import StudentCognitiveModel
from app.learning_agent.agent import LearningAgent


# Create student and Learning Agent
student = StudentCognitiveModel(user_id="student_001")
agent = LearningAgent()


def show_decision(title, concept_name, has_conflict=False):
    """
    Ask the Learning Agent to choose an action
    and print its decision.
    """

    concept = student.get_concept(concept_name)

    action = agent.choose_action(
        student=student,
        concept_name=concept_name,
        has_conflict=has_conflict
    )

    print(f"\n========== {title} ==========")
    print("Concept:", concept_name)
    print("Mastery:", concept.mastery)
    print("Confidence:", concept.confidence)
    print("Conflict:", has_conflict)

    print("\nLearning Agent Decision:")
    print("Action:", action.action_type)
    print("Difficulty:", action.difficulty)
    print("Reason:", action.reason)


# ==================================================
# TEST 1: LOW MASTERY
# ==================================================

recursion = student.get_concept("Recursion")

recursion.mastery = 0.25
recursion.confidence = 0.30

show_decision(
    "TEST 1 - LOW MASTERY",
    "Recursion"
)


# ==================================================
# TEST 2: MODERATE MASTERY
# ==================================================

recursion.mastery = 0.55
recursion.confidence = 0.40

show_decision(
    "TEST 2 - MODERATE MASTERY",
    "Recursion"
)


# ==================================================
# TEST 3: HIGH MASTERY, LOW CONFIDENCE
# ==================================================

recursion.mastery = 0.82
recursion.confidence = 0.30

show_decision(
    "TEST 3 - HIGH MASTERY BUT LOW CONFIDENCE",
    "Recursion"
)


# ==================================================
# TEST 4: HIGH MASTERY + HIGH CONFIDENCE
# ==================================================

recursion.mastery = 0.85
recursion.confidence = 0.75

show_decision(
    "TEST 4 - HIGH MASTERY AND CONFIDENCE",
    "Recursion"
)


# ==================================================
# TEST 5: CROSS-AGENT CONFLICT
# ==================================================

recursion.mastery = 0.80
recursion.confidence = 0.70

show_decision(
    "TEST 5 - CROSS-AGENT CONFLICT",
    "Recursion",
    has_conflict=True
)