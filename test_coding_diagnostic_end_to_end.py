from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.evidence import LearningEvidence
from app.cognitive.diagnostic_intervention import DiagnosticIntervention
from app.cognitive.cross_agent_runtime import CrossAgentRuntime
from app.coding_agent.diagnostic_bridge import CodingDiagnosticBridge
from app.learning_agent.quiz_models import QuizQuestion, EvaluationResult


class FakeQuizGenerator:
    def __init__(self):
        self.calls = 0

    def generate(self, **kwargs):
        self.calls += 1
        return QuizQuestion(
            concept_name="Recursion",
            difficulty="medium",
            question="What stops a recursive function from calling itself forever?",
            correct_answer="A base case.",
            explanation="A base case terminates recursive calls.",
        )


class FakeAnswerEvaluator:
    def __init__(self):
        self.calls = 0

    def evaluate(self, student_answer):
        self.calls += 1
        assert student_answer.answer == "A base case."
        return EvaluationResult(
            is_correct=True,
            performance=0.90,
            feedback="Correct. A base case stops recursion.",
            detected_misconceptions=[],
        )


student = StudentCognitiveModel(user_id="isolated_coding_diagnostic_test")
engine = CognitiveEngine()

assert not engine.has_conflict(student.user_id, "Recursion")

for agent, performance in [("learning", 0.90), ("coding", 0.20)]:
    engine.process_evidence(
        student=student,
        evidence=LearningEvidence(
            user_id=student.user_id,
            concept_name="Recursion",
            source_agent=agent,
            evidence_type="quiz" if agent == "learning" else "coding_solution",
            performance=performance,
            difficulty=0.70,
            reliability=0.90,
        ),
    )

assert engine.has_conflict(student.user_id, "Recursion")
print("PASS 1: Real cross-agent conflict detected.")

generator = FakeQuizGenerator()
evaluator = FakeAnswerEvaluator()

intervention = DiagnosticIntervention(
    cognitive_engine=engine,
    quiz_generator=generator,
    answer_evaluator=evaluator,
)

runtime = CrossAgentRuntime(
    cognitive_engine=engine,
    diagnostic_intervention=intervention,
)

bridge = CodingDiagnosticBridge(
    student=student,
    cognitive_engine=engine,
    cross_agent_runtime=runtime,
)

decision = bridge.start("Recursion")
session = decision.diagnostic_session

assert session is not None
assert session.question.concept_name == "Recursion"
assert generator.calls == 1
print("PASS 2: Diagnostic generated for genuine conflict.")

attempts_before = student.get_concept("Recursion").attempts

first = bridge.submit_answer(session, "A base case.")

assert evaluator.calls == 1
assert first.resolution.diagnostic_outcome.evaluation.performance == 0.90
assert student.get_concept("Recursion").attempts == attempts_before + 1
print("PASS 3: Diagnostic evaluated and processed by CACM exactly once.")

assert first.resolution.diagnostic_outcome.conflict_resolved
assert not first.has_active_conflict
assert not engine.has_conflict(student.user_id, "Recursion")
print("PASS 4: Real conflict resolved using diagnostic evidence.")

assert first.next_coding_action.action_type != "diagnostic_coding"
print(
    "PASS 5: Coding Agent replanned to",
    first.next_coding_action.action_type,
)

attempts_after = student.get_concept("Recursion").attempts
second = bridge.submit_answer(session, "A base case.")

assert evaluator.calls == 1
assert student.get_concept("Recursion").attempts == attempts_after
assert second.resolution.diagnostic_outcome is first.resolution.diagnostic_outcome
print("PASS 6: Duplicate submission did not update CACM again.")

print("\nALL SIX END-TO-END CODING DIAGNOSTIC CHECKS PASSED.")
