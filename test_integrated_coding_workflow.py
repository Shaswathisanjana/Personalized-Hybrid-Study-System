from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.models import StudentCognitiveModel

from app.coding_agent.integrated_workflow import IntegratedCodingWorkflow
from app.coding_agent.models import (
    CodingTask,
    CodingSubmission,
    CodingEvaluation,
)
from app.coding_agent.code_runner import BehavioralTestCase


def check(name, condition):
    assert condition, f"FAILED: {name}"
    print(f"PASS: {name}")


class FakeTaskGenerator:
    def __init__(self):
        self.calls = []

    def generate(self, concept_name, difficulty):
        self.calls.append((concept_name, difficulty))

        return CodingTask(
            concept_name=concept_name,
            title="Factorial using recursion",
            description="Write a recursive factorial function.",
            difficulty=difficulty,
        )


class FakeEvaluator:
    def __init__(self):
        self.calls = []
        self.performance = 0.90

    def evaluate(self, submission, test_cases):
        self.calls.append(submission)

        return CodingEvaluation(
            is_correct=self.performance >= 0.75,
            performance=self.performance,
            confidence=0.90,
            feedback="Mock assessment of the student's own code.",
            test_results=[],
            detected_misconceptions=[],
        )


class FakeGuidedReviewer:
    def __init__(self):
        self.calls = 0

    def review_submission(
        self,
        code,
        problem_description="",
        concept_name="",
        test_cases=None,
    ):
        self.calls += 1

        return {
            "feedback": "Mock AI correction and guidance.",
            "suggested_code": "AI-generated correction",
        }


student = StudentCognitiveModel(user_id="student_001")
engine = CognitiveEngine()

generator = FakeTaskGenerator()
evaluator = FakeEvaluator()
reviewer = FakeGuidedReviewer()

workflow = IntegratedCodingWorkflow(
    student=student,
    cognitive_engine=engine,
    task_generator=generator,
    evaluator=evaluator,
    guided_reviewer=reviewer,
)


# TEST 1: Coding Agent chooses a task using the shared model.
action, task = workflow.generate_task("Recursion")

check(
    "Task generated using Coding Agent decision",
    task.concept_name == "Recursion"
    and task.difficulty == action.difficulty
    and generator.calls == [("Recursion", action.difficulty)],
)


# TEST 2: Student submits original code.
original_code = (
    "def factorial(n):\n"
    "    if n <= 1:\n"
    "        return 1\n"
    "    return n * factorial(n - 1)"
)

submission = CodingSubmission(
    user_id="student_001",
    task=task,
    code=original_code,
)

tests = [
    BehavioralTestCase(
        test_name="Factorial three",
        function_name="factorial",
        args=[3],
        expected_output=6,
    )
]

before_attempts = student.get_concept("Recursion").attempts

result = workflow.submit_student_code(
    submission=submission,
    test_cases=tests,
    include_guided_review=True,
)

after_attempts = student.get_concept("Recursion").attempts

check(
    "Original student submission evaluated",
    len(evaluator.calls) == 1
    and evaluator.calls[0] is submission
    and result.evaluation.performance == 0.90,
)


# TEST 3: Evaluated student work reaches the real CACM engine.
check(
    "Shared cognitive model updated",
    after_attempts == before_attempts + 1
    and result.cognitive_outcome.concept_name == "Recursion"
    and result.cognitive_outcome.performance == 0.90,
)


# TEST 4: Guided review does not independently update CACM.
check(
    "AI review does not create extra mastery evidence",
    reviewer.calls == 1
    and student.get_concept("Recursion").attempts == after_attempts
    and result.guided_review is not None,
)


# TEST 5: Another student's submission is rejected.
other_submission = CodingSubmission(
    user_id="another_student",
    task=task,
    code=original_code,
)

calls_before = len(evaluator.calls)
attempts_before = student.get_concept("Recursion").attempts

try:
    workflow.submit_student_code(
        submission=other_submission,
        test_cases=tests,
    )
except ValueError:
    rejected = True
else:
    rejected = False

check(
    "Different student's submission rejected",
    rejected
    and len(evaluator.calls) == calls_before
    and student.get_concept("Recursion").attempts == attempts_before,
)


# TEST 6: Invalid behavioral tests are rejected.
try:
    workflow.submit_student_code(
        submission=submission,
        test_cases=["invalid"],
    )
except TypeError:
    invalid_tests_rejected = True
else:
    invalid_tests_rejected = False

check(
    "Invalid behavioral tests rejected",
    invalid_tests_rejected,
)


print("\nALL SIX INTEGRATED CODING WORKFLOW TESTS PASSED.")
