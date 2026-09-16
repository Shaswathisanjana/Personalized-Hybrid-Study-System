from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.evidence import LearningEvidence

from app.learning_agent.agent import LearningAgent
from app.learning_agent.gemini_quiz_generator import (
    GeminiQuizGenerator,
)
from app.learning_agent.quiz_models import StudentAnswer
from app.learning_agent.answer_evaluator import AnswerEvaluator


# ==========================================
# 1. CREATE STUDENT
# ==========================================

student = StudentCognitiveModel(
    user_id="student_001"
)

concept = student.get_concept("Recursion")

# Starting cognitive state
concept.mastery = 0.54
concept.confidence = 0.25


# ==========================================
# 2. CREATE SYSTEM COMPONENTS
# ==========================================

engine = CognitiveEngine()

learning_agent = LearningAgent()

quiz_generator = GeminiQuizGenerator()

evaluator = AnswerEvaluator()


print("\n========== INITIAL STATE ==========")

print("Mastery:", concept.mastery)
print("Confidence:", concept.confidence)


# ==========================================
# 3. LEARNING AGENT DECIDES WHAT TO DO
# ==========================================

has_conflict = engine.has_conflict(
    student.user_id,
    "Recursion",
)

action = learning_agent.choose_action(
    student=student,
    concept_name="Recursion",
    has_conflict=has_conflict,
)


print("\n========== AGENT DECISION ==========")

print("Action:", action.action_type)
print("Difficulty:", action.difficulty)
print("Reason:", action.reason)


# ==========================================
# 4. GEMINI GENERATES THE QUESTION
# ==========================================

question = quiz_generator.generate(
    concept_name="Recursion",
    difficulty=action.difficulty,
    mastery=concept.mastery,
    confidence=concept.confidence,
    quiz_type=action.action_type,
)


print("\n========== QUESTION ==========")

print(question.question)


# ==========================================
# 5. STUDENT ENTERS AN ACTUAL ANSWER
# ==========================================

student_response = input(
    "\nEnter your answer: "
)


student_answer = StudentAnswer(
    user_id=student.user_id,
    question=question,
    answer=student_response,
)


# ==========================================
# 6. AUTOMATIC ANSWER EVALUATION
# ==========================================

evaluation = evaluator.evaluate(
    student_answer
)


print("\n========== EVALUATION ==========")

print(
    "Correct:",
    evaluation.is_correct
)

print(
    "Performance:",
    evaluation.performance
)

print(
    "Feedback:",
    evaluation.feedback
)

print(
    "Detected Misconceptions:",
    evaluation.detected_misconceptions
)


# ==========================================
# 7. TURN RESULT INTO COGNITIVE EVIDENCE
# ==========================================

evidence = LearningEvidence(
    user_id=student.user_id,
    concept_name="Recursion",
    source_agent="learning",
    evidence_type=action.action_type,
    performance=evaluation.performance,
    difficulty=0.5,
    reliability=0.7,
)

result = engine.process_evidence(
    student=student,
    evidence=evidence,
)


# ==========================================
# 8. SHOW UPDATED COGNITIVE STATE
# ==========================================

updated = result["concept"]


print("\n========== UPDATED COGNITIVE STATE ==========")

print(
    "Mastery:",
    updated.mastery
)

print(
    "Confidence:",
    updated.confidence
)

print(
    "Attempts:",
    updated.attempts
)


# ==========================================
# 9. AGENT RE-PLANS
# ==========================================

new_conflict = engine.has_conflict(
    student.user_id,
    "Recursion",
)

next_action = learning_agent.choose_action(
    student=student,
    concept_name="Recursion",
    has_conflict=new_conflict,
)


print("\n========== NEXT AGENT DECISION ==========")

print(
    "Action:",
    next_action.action_type
)

print(
    "Difficulty:",
    next_action.difficulty
)

print(
    "Reason:",
    next_action.reason
)