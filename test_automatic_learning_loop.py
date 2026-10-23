from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.evidence import LearningEvidence

from app.learning_agent.agent import LearningAgent
from app.learning_agent.gemini_quiz_generator import (
    GeminiQuizGenerator,
)
from app.learning_agent.answer_evaluator import (
    AnswerEvaluator,
)
from app.learning_agent.misconception_analyzer import (
    MisconceptionAnalyzer,
)
from app.learning_agent.quiz_models import (
    StudentAnswer,
)


# ==================================================
# SETUP
# ==================================================

student = StudentCognitiveModel(
    user_id="student_001"
)

concept = student.get_concept(
    "Recursion"
)

# Starting cognitive state
concept.mastery = 0.54
concept.confidence = 0.25


engine = CognitiveEngine()

learning_agent = LearningAgent()

quiz_generator = GeminiQuizGenerator()

answer_evaluator = AnswerEvaluator()

misconception_analyzer = MisconceptionAnalyzer()


# ==================================================
# STEP 1: SHOW INITIAL COGNITIVE STATE
# ==================================================

print(
    "\n========== INITIAL COGNITIVE STATE =========="
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


# ==================================================
# STEP 2: LEARNING AGENT DECIDES WHAT TO DO
# ==================================================

has_conflict = engine.has_conflict(
    student.user_id,
    "Recursion",
)

action = learning_agent.choose_action(
    student=student,
    concept_name="Recursion",
    has_conflict=has_conflict,
)


print(
    "\n========== LEARNING AGENT DECISION =========="
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
# STEP 3: GEMINI GENERATES QUIZ
# ==================================================

question = quiz_generator.generate(
    concept_name="Recursion",
    difficulty=action.difficulty,
    mastery=concept.mastery,
    confidence=concept.confidence,
    quiz_type=action.action_type,
)


print(
    "\n========== QUESTION =========="
)

print(
    question.question
)


# ==================================================
# STEP 4: STUDENT ANSWERS
# ==================================================

student_response = input(
    "\nEnter your answer: "
)


student_answer = StudentAnswer(
    user_id=student.user_id,
    question=question,
    answer=student_response,
)


# ==================================================
# STEP 5: OBJECTIVE ANSWER EVALUATION
# ==================================================

evaluation = answer_evaluator.evaluate(
    student_answer
)


print(
    "\n========== ANSWER EVALUATION =========="
)

print(
    "Correct:",
    evaluation.is_correct,
)

print(
    "Performance:",
    evaluation.performance,
)

print(
    "Feedback:",
    evaluation.feedback,
)


# ==================================================
# STEP 6: MISCONCEPTION ANALYSIS
# ==================================================

detected_misconceptions = []


# Only analyze misconceptions when
# the student's answer is incorrect.
if not evaluation.is_correct:

    detected_misconceptions = (
        misconception_analyzer.analyze(
            student_answer
        )
    )


print(
    "\n========== MISCONCEPTION ANALYSIS =========="
)

if detected_misconceptions:

    for misconception in detected_misconceptions:

        print(
            "-",
            misconception,
        )

else:

    print(
        "No supported misconception detected."
    )


# ==================================================
# STEP 7: CONVERT DIFFICULTY TO NUMERIC VALUE
# ==================================================

difficulty_map = {
    "easy": 0.3,
    "medium": 0.5,
    "hard": 0.8,
}


numeric_difficulty = difficulty_map.get(
    action.difficulty,
    0.5,
)


# ==================================================
# STEP 8: CREATE LEARNING EVIDENCE
# ==================================================

evidence = LearningEvidence(
    user_id=student.user_id,

    concept_name="Recursion",

    source_agent="learning",

    evidence_type=action.action_type,

    performance=evaluation.performance,

    difficulty=numeric_difficulty,

    reliability=0.7,

    detected_misconceptions=(
        detected_misconceptions
    ),
)


# ==================================================
# STEP 9: UPDATE SHARED COGNITIVE MODEL
# ==================================================

result = engine.process_evidence(
    student=student,
    evidence=evidence,
)


updated_concept = result[
    "concept"
]


print(
    "\n========== UPDATED COGNITIVE STATE =========="
)

print(
    "Mastery:",
    updated_concept.mastery,
)

print(
    "Confidence:",
    updated_concept.confidence,
)

print(
    "Attempts:",
    updated_concept.attempts,
)

print(
    "Misconceptions:",
    updated_concept.misconceptions,
)


# ==================================================
# STEP 10: LEARNING AGENT RE-PLANS
# ==================================================

next_action = learning_agent.choose_action(
    student=student,

    concept_name="Recursion",

    has_conflict=engine.has_conflict(
        student.user_id,
        "Recursion",
    ),
)


print(
    "\n========== NEXT AGENT DECISION =========="
)

print(
    "Action:",
    next_action.action_type,
)

print(
    "Difficulty:",
    next_action.difficulty,
)

print(
    "Reason:",
    next_action.reason,
)