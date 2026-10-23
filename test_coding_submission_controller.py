from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine

from app.coding_agent.models import CodingEvaluation
from app.coding_agent.integrated_workflow import IntegratedCodingWorkflow
from app.coding_agent.submission_controller import CodingSubmissionController
from app.coding_agent.verified_exercises import get_verified_exercise


class FakeEvaluator:
    def __init__(self):
        self.calls = 0

    def evaluate(self, submission, test_cases):
        self.calls += 1

        return CodingEvaluation(
            is_correct=True,
            performance=1.0,
            confidence=0.9,
            feedback="All supplied tests passed.",
        )


student = StudentCognitiveModel(
    user_id="coding_duplicate_test_student"
)

engine = CognitiveEngine()

evaluator = FakeEvaluator()

workflow = IntegratedCodingWorkflow(
    student=student,
    cognitive_engine=engine,
    evaluator=evaluator,
)

exercise = get_verified_exercise("Recursion")

controller = CodingSubmissionController(
    workflow=workflow,
    exercise=exercise,
)

code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""

before = student.get_concept("Recursion").attempts

first_record, first_is_new = controller.submit(code)

after_first = student.get_concept("Recursion").attempts

second_record, second_is_new = controller.submit(code)

after_second = student.get_concept("Recursion").attempts

assert first_is_new is True
assert second_is_new is False

assert first_record is second_record

assert evaluator.calls == 1

assert after_first == before + 1
assert after_second == after_first

print("PASS: First submission assessed")
print("PASS: Duplicate submission returned cached result")
print("PASS: Evaluator called only once")
print("PASS: CACM attempts increased only once")
print()
print("ALL SUBMISSION CONTROLLER TESTS PASSED.")
