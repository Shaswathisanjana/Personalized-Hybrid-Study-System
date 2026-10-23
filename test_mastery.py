from app.cognitive.models import StudentCognitiveModel
from app.cognitive.mastery_engine import MasteryEngine


# Create a student
student = StudentCognitiveModel(user_id="student_001")

# Create the mastery engine
engine = MasteryEngine()


# Check Recursion BEFORE receiving evidence
recursion = student.get_concept("Recursion")

print("----- BEFORE UPDATE -----")
print("Concept:", recursion.concept_name)
print("Mastery:", recursion.mastery)
print("Confidence:", recursion.confidence)
print("Attempts:", recursion.attempts)


# Suppose the student performs very well
# on a Recursion assessment.
engine.update_mastery(
    student=student,
    concept_name="Recursion",
    observed_performance=0.90,
    evidence_reliability=0.60,
)


# Check Recursion AFTER receiving evidence
recursion = student.get_concept("Recursion")

print("\n----- AFTER UPDATE -----")
print("Concept:", recursion.concept_name)
print("Mastery:", recursion.mastery)
print("Confidence:", recursion.confidence)
print("Attempts:", recursion.attempts)