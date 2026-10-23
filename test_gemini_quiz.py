from app.learning_agent.gemini_quiz_generator import (
    GeminiQuizGenerator,
)


generator = GeminiQuizGenerator()


question = generator.generate(
    concept_name="Recursion",
    difficulty="medium",
    mastery=0.54,
    confidence=0.25,
)


print("\n========== STUDENT VIEW ==========")

print("Concept:", question.concept_name)
print("Difficulty:", question.difficulty)

print("\nQuestion:")
print(question.question)


print("\n========== INTERNAL SYSTEM VIEW ==========")

print("Correct Answer:")
print(question.correct_answer)

print("\nExplanation:")
print(question.explanation)

print("\nMisconception Targets:")
print(question.misconception_targets)