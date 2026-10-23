"""Deterministic packages; verification uses real Python subprocesses, no provider calls."""
from copy import deepcopy
from types import SimpleNamespace
import json
import unittest
from unittest.mock import patch

from app.coding_agent.open_topic import (
    OpenTopicGenerator, PackageGenerationError, validate_package, normalize_topic, observe_action,
)
from app.coding_agent.integrated_workflow import IntegratedCodingWorkflow
from app.coding_agent.submission_controller import CodingSubmissionController
from app.coding_agent.adaptive_hint_coordinator import MisconceptionAwareHintCoordinator
from app.coding_agent.guided_review_coordinator import GuidedCodeReviewCoordinator
from app.coding_agent.ai_code_reviewer import AIReviewResult
from app.persistence.state_codec import encode, decode
from test_student_persistence import student_state


def package(difficulty="easy"):
    return dict(language="Python", difficulty=difficulty, title="Merge Two Sorted Lists",
                description="Merge sorted integer lists without mutating the inputs.",
                input_output="Two integer lists; return a sorted merged list.",
                constraints="Each list has at most 100 integers, already sorted ascending.",
                expected_behavior="Keep duplicate values and handle empty inputs.", function_name="merge_lists",
                starter_code="def merge_lists(a, b):\n    pass\n",
                reference_code="def merge_lists(a, b):\n    return sorted(a + b)\n",
                hints=["Track one position in each input.", "Handle either empty input.",
                       "Append the smaller next item, then the remaining tail."],
                tests=[dict(name="empty boundary", args=[[], []], expected_output=[]),
                       dict(name="interleaved", args=[[1, 3], [2, 4]], expected_output=[1, 2, 3, 4]),
                       dict(name="duplicates", args=[[2], [2]], expected_output=[2, 2])],
                example_test_indices=[0, 1])


class OpenTopicTests(unittest.TestCase):
    def test_decorator_topic_uses_executable_decorator_fixture(self):
        candidate = package()
        candidate.update(title="Apply an Increment Twice", function_name="increment_twice",
            description="Use a decorator to apply an integer increment function twice.",
            input_output="An integer; return that integer plus two.",
            constraints="Input is between -100 and 100.", expected_behavior="Apply the decorated increment twice.",
            starter_code="def increment_twice(n):\n    pass\n",
            reference_code=("def twice(fn):\n    def wrapped(n):\n        return fn(fn(n))\n    return wrapped\n"
                            "@twice\ndef increment_twice(n):\n    return n + 1\n"),
            tests=[dict(name="zero boundary", args=[0], expected_output=2),
                   dict(name="positive", args=[3], expected_output=5),
                   dict(name="negative", args=[-4], expected_output=-2)],
            hints=["Wrap a callable.", "Apply it to its own result.", "Return the wrapper from the decorator."])
        exercise = OpenTopicGenerator(lambda **kw: candidate).generate("Python decorators", "easy")
        self.assertEqual(exercise.task.concept_name, "python decorators")
        self.assertIn("3/3", exercise.validation_summary)

    def test_binary_tree_topic_uses_executable_tree_fixture(self):
        candidate = package()
        candidate.update(title="Search a Serialized BST", function_name="contains",
            description="Determine whether a value is present in a binary search tree.",
            input_output="A tree and integer target; return a Boolean. Tree is [] or [value,left,right].",
            constraints="Valid BST with at most 20 nodes and no duplicate keys.",
            expected_behavior="Return False for an empty tree; search the appropriate branch.",
            starter_code="def contains(tree, value):\n    pass\n",
            reference_code=("def contains(tree, value):\n    if not tree: return False\n"
                            "    if value == tree[0]: return True\n"
                            "    return contains(tree[1] if value < tree[0] else tree[2], value)\n"),
            tests=[dict(name="empty boundary", args=[[], 1], expected_output=False),
                   dict(name="left branch", args=[[3, [1, [], []], [5, [], []]], 1], expected_output=True),
                   dict(name="missing", args=[[3, [1, [], []], [5, [], []]], 4], expected_output=False)],
            hints=["An empty tree has no keys.", "Compare with the root.", "Search the left or right subtree."])
        exercise = OpenTopicGenerator(lambda **kw: candidate).generate("Binary Search Trees", "easy")
        self.assertEqual(exercise.task.concept_name, "binary search trees")
        self.assertIn("3/3", exercise.validation_summary)

    def test_normalization_is_conservative(self):
        self.assertEqual(normalize_topic("  Python   Recursion "), "Recursion")
        self.assertEqual(normalize_topic(" Binary Search Trees "), "binary search trees")
        self.assertNotEqual(normalize_topic("linked lists"), normalize_topic("arrays"))
        with self.assertRaises(ValueError):
            normalize_topic("x" * 161)

    def test_real_reference_validation_and_roundtrip(self):
        exercise = validate_package(package(), "merge sort", "easy")
        self.assertIn("3/3", exercise.validation_summary)
        self.assertIn("Examples", exercise.task.description)
        self.assertEqual(decode(encode(exercise)), exercise)
        hints = MisconceptionAwareHintCoordinator()
        for level in range(1, 4):
            hint = hints.get_next_hint(exercise.task, exercise.task.starter_code, "alice").hint
            self.assertEqual(hint.level, level)
            self.assertEqual(hint.message, exercise.task.progressive_hints[level-1])

    def test_incorrect_reference_is_never_verified(self):
        candidate = package()
        candidate["reference_code"] = "def merge_lists(a, b):\n    return []"
        with self.assertRaisesRegex(ValueError, "Reference solution failed"):
            validate_package(candidate, "merge sort", "easy")

    def test_completed_starter_rejected(self):
        candidate = package()
        candidate["starter_code"] = candidate["reference_code"]
        with self.assertRaisesRegex(ValueError, "Starter"):
            validate_package(candidate, "merge sort", "easy")

    def test_weak_constant_none_tests_rejected(self):
        candidate = package()
        for test in candidate["tests"]:
            test["expected_output"] = None
        candidate["reference_code"] = "def merge_lists(a, b):\n    return None"
        candidate["starter_code"] = "def merge_lists(a, b):\n    return 42"
        with self.assertRaisesRegex(ValueError, "constant None"):
            validate_package(candidate, "merge sort", "easy")

    def test_structural_invalid_packages(self):
        for mutate in (
            lambda p: p.update(language="SQL"),
            lambda p: p.update(difficulty="hard"),
            lambda p: p.update(hints=[]),
            lambda p: p.update(example_test_indices=[9]),
            lambda p: p.update(reference_code="import os\ndef merge_lists(a,b): return []"),
            lambda p: p.update(reference_code="def merge_lists(a,b): return open('private')"),
            lambda p: p.update(tests=p["tests"][:2]),
            lambda p: p["tests"].__setitem__(1, p["tests"][0]),
            lambda p: p["tests"][0].update(expected_output=float("nan")),
        ):
            with self.subTest(mutate=mutate):
                candidate = package()
                mutate(candidate)
                with self.assertRaises((ValueError, SyntaxError)):
                    validate_package(candidate, "merge sort", "easy")

    def test_actual_nontermination_rejected(self):
        from app.coding_agent.code_runner import ControlledCodeRunner
        candidate = package()
        candidate["reference_code"] = "def merge_lists(a,b):\n    while True: pass"
        with self.assertRaisesRegex(ValueError, "Reference solution failed"):
            validate_package(candidate, "merge sort", "easy", ControlledCodeRunner(timeout_seconds=.3))

    def test_bounded_retry_then_valid_package(self):
        calls = []
        def provider(**request):
            calls.append(request)
            return "not JSON" if len(calls) == 1 else json.dumps(package("medium"))
        exercise = OpenTopicGenerator(provider).generate("merge sort", "medium")
        self.assertEqual(exercise.task.difficulty, "medium")
        self.assertEqual(len(calls), 2)
        self.assertTrue(calls[1]["feedback"])

    def test_failure_is_bounded_redacted_and_does_not_mutate_cacm(self):
        state = student_state("alice")
        workflow = IntegratedCodingWorkflow(state["student"], state["orchestrator"].cognitive_engine)
        before = encode(workflow.student)
        action = observe_action(workflow, "binary search trees")
        calls = []
        def provider(**request):
            calls.append(request)
            raise RuntimeError("secret credential must not appear")
        with self.assertRaises(PackageGenerationError) as error:
            OpenTopicGenerator(provider, max_attempts=2).generate(action.concept_name, action.difficulty)
        self.assertEqual(len(calls), 2)
        self.assertNotIn("secret", str(error.exception))
        self.assertEqual(encode(workflow.student), before)
        self.assertEqual(workflow.cognitive_engine.evidence_store.get_all_evidence(), [])

    def test_shared_cacm_difficulty_is_actually_used(self):
        state = student_state("alice")
        concept = state["student"].get_concept("merge sort")
        concept.mastery, concept.confidence, concept.attempts = .95, .9, 5
        workflow = IntegratedCodingWorkflow(state["student"], state["orchestrator"].cognitive_engine)
        before = encode(workflow.student)
        action = observe_action(workflow, " MERGE SORT ")
        self.assertEqual(action.difficulty, "hard")
        calls = []
        def provider(**request):
            calls.append(request)
            return package(request["difficulty"])
        exercise = OpenTopicGenerator(provider).generate(action.concept_name, action.difficulty)
        self.assertEqual(calls[0]["difficulty"], "hard")
        self.assertEqual(exercise.task.difficulty, "hard")
        self.assertEqual(before, encode(workflow.student))

    def test_unsupported_language_makes_no_provider_call(self):
        def forbidden(**request):
            self.fail("Unsupported language called the provider")
        with self.assertRaisesRegex(ValueError, "not supported"):
            OpenTopicGenerator(forbidden).generate("SQL joins", "easy", "SQL")

    def test_package_ids_separate_different_exercises(self):
        state = student_state("alice")
        workflow = IntegratedCodingWorkflow(state["student"], state["orchestrator"].cognitive_engine)
        first = validate_package(package(), "merge sort", "easy")
        other = package()
        other["tests"][1].update(args=[[5], [6]], expected_output=[5, 6])
        second = validate_package(other, "merge sort", "easy")
        self.assertNotEqual(CodingSubmissionController(workflow, first)._submission_id("same code"),
                            CodingSubmissionController(workflow, second)._submission_id("same code"))

    def test_correction_verification_is_not_student_evidence(self):
        exercise = validate_package(package(), "merge sort", "easy")
        state = student_state("alice")
        before = encode(state["student"])
        reviewer = SimpleNamespace(review=lambda **kw: AIReviewResult("Use sorted merge", corrected_code=exercise.reference_code))
        guided = GuidedCodeReviewCoordinator(reviewer=reviewer).review_submission(
            exercise.task.starter_code, exercise.task.description, "merge sort", exercise.test_cases)
        self.assertEqual(guided.correction_status, "passed_supplied_tests")
        self.assertEqual(before, encode(state["student"]))
        self.assertEqual(state["orchestrator"].cognitive_engine.evidence_store.get_all_evidence(), [])

    def test_existing_provider_transport_configuration(self):
        calls = []
        client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kw:
            calls.append(kw) or SimpleNamespace(text=json.dumps(package()))))
        with patch("app.coding_agent.open_topic.CodingTaskGenerator",
                   return_value=SimpleNamespace(client=client, model_name="existing-model")):
            exercise = OpenTopicGenerator().generate("merge sort", "easy")
        self.assertEqual(exercise.task.concept_name, "merge sort")
        self.assertEqual(calls[0]["model"], "existing-model")
        self.assertEqual(calls[0]["config"]["http_options"]["timeout"], 30000)


if __name__ == "__main__":
    unittest.main()
