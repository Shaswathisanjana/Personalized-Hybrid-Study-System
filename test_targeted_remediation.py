from app.cognitive.models import (
    StudentCognitiveModel,
)

from app.learning_agent.agent import (
    LearningAgent,
)

from app.learning_agent.content_generator import (
    PersonalizedContentGenerator,
)


student = StudentCognitiveModel(
    user_id="student_001"
)

concept = student.get_concept(
    "Recursion"
)

concept.mastery = 0.257
concept.confidence = 0.302

concept.misconceptions.append(
    "Incorrectly reducing the recursive step "
    "value by confusing n-2 with n-1"
)


agent = LearningAgent()

generator = PersonalizedContentGenerator()


action = agent.choose_action(
    student=student,
    concept_name="Recursion",
    has_conflict=False,
)


content = generator.generate(
    student=student,
    action=action,
)


print(
    "\n========== COGNITIVE STATE =========="
)

print(
    "Mastery:",
    concept.mastery,
)

print(
    "Confidence:",
    concept.confidence,
)

print(
    "Misconceptions:",
    concept.misconceptions,
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
    "\n========== CONTENT TYPE =========="
)

print(
    content.content_type
)


print(
    "\n========== GENERATED REQUEST =========="
)

print(
    content.text
)


print(
    "\n========== COGNITIVE CONTEXT =========="
)

print(
    content.cognitive_context
)