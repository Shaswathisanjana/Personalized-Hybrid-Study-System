from app.cognitive.models import (
    StudentCognitiveModel,
)

from app.learning_agent.agent import (
    LearningAgent,
)

from app.learning_agent.content_generator import (
    PersonalizedContentGenerator,
)

from app.learning_agent.gemini_provider import (
    GeminiContentProvider,
)


# ==================================================
# STEP 1: CREATE STUDENT
# ==================================================

student = StudentCognitiveModel(
    user_id="student_001"
)

concept = student.get_concept(
    "Recursion"
)

concept.mastery = 0.257
concept.confidence = 0.302
concept.attempts = 1

concept.misconceptions.append(
    "Incorrectly reducing the recursive step value "
    "by confusing n-2 with n-1"
)


# ==================================================
# STEP 2: CREATE COMPONENTS
# ==================================================

learning_agent = LearningAgent()

content_generator = PersonalizedContentGenerator()

gemini_provider = GeminiContentProvider()


# ==================================================
# STEP 3: AGENT DECIDES NEXT ACTION
# ==================================================

action = learning_agent.choose_action(
    student=student,
    concept_name="Recursion",
    has_conflict=False,
)


print(
    "\n========== AGENT DECISION =========="
)

print(
    "Action:",
    action.action_type,
)

print(
    "Difficulty:",
    action.difficulty,
)

print(
    "Reason:",
    action.reason,
)


# ==================================================
# STEP 4: BUILD PERSONALIZED REQUEST
# ==================================================

generated_request = content_generator.generate(
    student=student,
    action=action,
)


print(
    "\n========== CONTENT STRATEGY =========="
)

print(
    generated_request.content_type
)


print(
    "\n========== PERSONALIZED REQUEST =========="
)

print(
    generated_request.text
)


# ==================================================
# STEP 5: GEMINI CREATES ACTUAL LESSON
# ==================================================

lesson = gemini_provider.create_content(
    generated_request
)


print(
    "\n========== GEMINI TARGETED LESSON =========="
)

print(
    lesson
)
