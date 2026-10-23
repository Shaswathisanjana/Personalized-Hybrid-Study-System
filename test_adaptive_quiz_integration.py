from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine
from app.learning_agent.runtime import LearningAgentRuntime
from app.learning_agent.quiz_models import QuizQuestion, EvaluationResult


class FakeQuizGenerator:
    def __init__(self):
        self.calls = []

    def generate(
        self,
        concept_name,
        difficulty,
        mastery,
        confidence,
        quiz_type,
        previous_questions=None,
        target_misconceptions=None,
        learning_context=None,
    ):
        history = previous_questions or []

        self.calls.append({
            "difficulty": difficulty,
            "mastery": mastery,
            "confidence": confidence,
            "history_length": len(history),
            "targets": list(target_misconceptions or []),
        })

        number = len(self.calls)

        return QuizQuestion(
            concept_name=concept_name,
            difficulty=difficulty,
            question=f"Controlled question {number}",
            correct_answer=f"answer {number}",
            explanation="Controlled integration-test question.",
        )


class FakeAnswerEvaluator:
    def evaluate(self, student_answer):
        correct = (
            student_answer.answer.strip().lower()
            == student_answer.question.correct_answer.lower()
        )

        return EvaluationResult(
            is_correct=correct,
            performance=1.0 if correct else 0.0,
            feedback="Correct." if correct else "Incorrect.",
            detected_misconceptions=[],
        )


class FakeMisconceptionAnalyzer:
    def analyze(self, student_answer):
        return ["Needs to review the underlying concept."]


class NoExternalResources:
    def recommend(self, *args, **kwargs):
        raise AssertionError(
            "External resource retrieval should not occur in this test."
        )


student = StudentCognitiveModel(
    user_id="adaptive_integration_test"
)

engine = CognitiveEngine()
generator = FakeQuizGenerator()

runtime = LearningAgentRuntime(
    cognitive_engine=engine,
    quiz_generator=generator,
    answer_evaluator=FakeAnswerEvaluator(),
    misconception_analyzer=FakeMisconceptionAnalyzer(),
    resource_recommender=NoExternalResources(),
)

concept = "Python recursion"

print("\n========== START FIVE-QUESTION SESSION ==========")

start = runtime.start_practice_session(
    student=student,
    concept_name=concept,
    max_questions=5,
)

session = start.session

assert session.max_questions == 5
assert len(generator.calls) == 1
assert generator.calls[0]["history_length"] == 0

print("PASS: Only the first question was generated initially.")

print("\n========== SEQUENTIAL ADAPTIVE ASSESSMENT ==========")

# Mix correct and incorrect answers to exercise adaptive behavior.
answer_pattern = [True, False, True, True, False]

for index, should_be_correct in enumerate(answer_pattern, start=1):
    question = session.current_question

    assert question is not None

    before_attempts = student.get_concept(concept).attempts
    before_generation_count = len(generator.calls)

    answer = (
        question.correct_answer
        if should_be_correct
        else "controlled incorrect response"
    )

    outcome = runtime.submit_practice_session_answer(
        student=student,
        session=session,
        answer=answer,
    )

    after_attempts = student.get_concept(concept).attempts

    assert after_attempts == before_attempts + 1
    assert session.questions_completed == index
    assert len(session.attempts) == index
    assert outcome.assessment.evidence.source_agent == "learning"
    assert outcome.assessment.evidence.evidence_type == "practice_quiz"

    if index < 5:
        assert not session.is_complete
        assert outcome.next_question is not None
        assert len(generator.calls) == before_generation_count + 1

        # The generator receives the history AFTER the previous
        # answer has been evaluated and recorded.
        assert generator.calls[-1]["history_length"] == index

        # It also receives the student's updated CACM values.
        current_state = student.get_concept(concept)

        assert (
            generator.calls[-1]["mastery"]
            == current_state.mastery
        )
        assert (
            generator.calls[-1]["confidence"]
            == current_state.confidence
        )

    else:
        assert session.is_complete
        assert outcome.next_question is None
        assert outcome.summary is not None
        assert len(generator.calls) == 5
        assert session.questions_remaining == 0

    print(
        f"PASS: Q{index}/5 | "
        f"performance={outcome.assessment.evaluation.performance:.1f} | "
        f"CACM attempts={after_attempts} | "
        f"complete={session.is_complete}"
    )

print("\n========== COMPLETED SESSION PROTECTION ==========")

try:
    runtime.submit_practice_session_answer(
        student=student,
        session=session,
        answer="extra answer",
    )
except ValueError:
    print("PASS: Additional answer rejected after completion.")
else:
    raise AssertionError(
        "Completed session incorrectly accepted another answer."
    )

assert len(generator.calls) == 5
assert student.get_concept(concept).attempts == 5

print("\nSTEP 54 FULL ADAPTIVE INTEGRATION TEST PASSED")
