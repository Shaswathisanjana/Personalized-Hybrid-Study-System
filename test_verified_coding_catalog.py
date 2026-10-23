"""Offline reference/negative checks for every curated coding task and hint set."""
import json
from types import SimpleNamespace
import unittest

from app.coding_agent.verified_exercises import get_verified_exercise, VERIFIED_CONCEPTS
from app.coding_agent.code_runner import ControlledCodeRunner, BehavioralTestCase
from app.coding_agent.agent import CodingAgent
from app.coding_agent.evaluator import CodingEvaluator
from app.coding_agent.models import CodingSubmission
from app.coding_agent.static_analyzer import CodingStaticAnalyzer
from app.coding_agent.progressive_hint_engine import ProgressiveHintEngine
from app.coding_agent.agentic_review_coordinator import AgenticCodeReviewCoordinator
from app.cognitive.models import StudentCognitiveModel
from app.cognitive.cognitive_engine import CognitiveEngine


# Controlled solutions for reproducible verification, never imported by the app.
SOLUTIONS = {
    ("Recursion", "easy"): "def factorial(n):\n    return 1 if n == 0 else n * factorial(n-1)",
    ("Recursion", "medium"): "def sum_nested(values):\n    return sum(sum_nested(v) if isinstance(v,list) else v for v in values)",
    ("Recursion", "hard"): '''def recursive_search(nums, target):
    def search(left, right):
        if left > right: return -1
        mid = (left + right) // 2
        if nums[mid] == target: return mid
        return search(left, mid-1) if target < nums[mid] else search(mid+1, right)
    return search(0, len(nums)-1)
''',
    ("Prime Numbers", "easy"): "def is_prime(n):\n    return n >= 2 and all(n % d for d in range(2, int(n**0.5)+1))",
    ("Prime Numbers", "medium"): '''def prime_factors(n):
    answer, divisor = [], 2
    while divisor * divisor <= n:
        while n % divisor == 0:
            answer.append(divisor)
            n //= divisor
        divisor += 1
    if n > 1: answer.append(n)
    return answer
''',
    ("Prime Numbers", "hard"): '''def primes_in_range(start, end):
    if end < 2 or start > end: return []
    sieve = [True] * (end+1)
    sieve[0] = sieve[1] = False
    for p in range(2, int(end**0.5)+1):
        if sieve[p]:
            for multiple in range(p*p, end+1, p): sieve[multiple] = False
    return [n for n in range(max(2, start), end+1) if sieve[n]]
''',
    ("Arrays", "easy"): '''def find_max(nums):
    largest = nums[0]
    for value in nums[1:]:
        if value > largest: largest = value
    return largest
''',
    ("Arrays", "medium"): "def rotate_right(nums,k):\n    if not nums: return []\n    k %= len(nums)\n    return nums[-k:]+nums[:-k] if k else nums[:]",
    ("Arrays", "hard"): '''def max_subarray_sum(nums):
    ending = best = nums[0]
    for value in nums[1:]:
        ending = max(value, ending + value)
        best = max(best, ending)
    return best
''',
    ("Strings", "easy"): "def count_vowels(text):\n    return sum(c.lower() in 'aeiou' for c in text)",
    ("Strings", "medium"): "def are_anagrams(left,right):\n    return sorted(c.lower() for c in left if not c.isspace()) == sorted(c.lower() for c in right if not c.isspace())",
    ("Strings", "hard"): '''def longest_unique_length(text):
    seen, left, best = {}, 0, 0
    for right, char in enumerate(text):
        left = max(left, seen.get(char, -1) + 1)
        seen[char] = right
        best = max(best, right - left + 1)
    return best
''',
    ("Python Functions", "easy"): "def clamp(value,lower,upper):\n    return min(upper,max(lower,value))",
    ("Python Functions", "medium"): '''def calculate(operation,a,b):
    if operation == 'add': return a+b
    if operation == 'subtract': return a-b
    if operation == 'multiply': return a*b
    return a/b
''',
    ("Python Functions", "hard"): '''def run_pipeline(value, operations):
    def add(a,b): return a+b
    def multiply(a,b): return a*b
    def subtract(a,b): return a-b
    functions = dict(add=add, multiply=multiply, subtract=subtract)
    for operation, operand in operations: value = functions[operation](value, operand)
    return value
''',
    ("Searching Algorithms", "easy"): "def linear_search(nums,target):\n    return next((i for i,v in enumerate(nums) if v == target),-1)",
    ("Searching Algorithms", "medium"): '''def binary_search(nums,target):
    left, right = 0, len(nums)-1
    while left <= right:
        mid = (left + right)//2
        if nums[mid] == target: return mid
        if nums[mid] < target: left = mid + 1
        else: right = mid - 1
    return -1
''',
    ("Searching Algorithms", "hard"): '''def lower_bound(nums,target):
    left, right = 0, len(nums)
    while left < right:
        mid = (left + right)//2
        if nums[mid] < target: left = mid + 1
        else: right = mid
    return left
''',
}


class VerifiedCatalogTests(unittest.TestCase):
    def test_all_eighteen_reference_solutions_pass_actual_subprocess_tests(self):
        runner = ControlledCodeRunner()
        self.assertEqual(len(SOLUTIONS), len(VERIFIED_CONCEPTS) * 3)
        for (concept, difficulty), code in SOLUTIONS.items():
            with self.subTest(concept=concept, difficulty=difficulty):
                exercise = get_verified_exercise(concept, difficulty)
                result = runner.run_tests(code, exercise.test_cases)
                self.assertEqual(result.passed_count, len(exercise.test_cases), result)

    def test_starters_are_not_solutions_and_cases_reject_them(self):
        runner = ControlledCodeRunner()
        for concept, difficulty in SOLUTIONS:
            with self.subTest(concept=concept, difficulty=difficulty):
                exercise = get_verified_exercise(concept, difficulty)
                result = runner.run_tests(exercise.task.starter_code, exercise.test_cases[:1])
                self.assertEqual(result.passed_count, 0)

    def test_levels_are_distinct_and_aliases_are_conservative(self):
        for concept in VERIFIED_CONCEPTS:
            exercises = [get_verified_exercise(concept, level) for level in ("easy", "medium", "hard")]
            self.assertEqual(len({e.task.title for e in exercises}), 3)
            self.assertEqual(len({e.task.description for e in exercises}), 3)
        self.assertEqual(get_verified_exercise("python recursion", " HARD ").task.title, "Recursive Binary Search")
        with self.assertRaises(ValueError): get_verified_exercise("Python Lists")
        with self.assertRaises(ValueError): get_verified_exercise("Arrays", "expert")

    def test_returned_exercises_are_independent(self):
        first = get_verified_exercise("Arrays", "medium")
        first.test_cases[1].args[0].append(999)
        second = get_verified_exercise("Arrays", "medium")
        self.assertNotIn(999, second.test_cases[1].args[0])

    def test_each_exercise_has_three_matching_hints_without_evidence(self):
        student = StudentCognitiveModel("alice")
        engine = ProgressiveHintEngine()
        for concept, difficulty in SOLUTIONS:
            exercise = get_verified_exercise(concept, difficulty)
            messages = [engine.get_next_hint(exercise.task, "alice").message for _ in range(3)]
            self.assertEqual(len(set(messages)), 3)
            if difficulty != "easy":
                self.assertFalse(any("factorial(0)" in message for message in messages))
        self.assertEqual(student.concepts, {})

    def test_review_mapping_covers_exact_supported_identities(self):
        for concept in VERIFIED_CONCEPTS:
            self.assertEqual(AgenticCodeReviewCoordinator.normalize_concept(concept.upper()), concept)
        self.assertEqual(AgenticCodeReviewCoordinator.normalize_concept("factorial"), "")
        self.assertEqual(AgenticCodeReviewCoordinator.normalize_concept("Python Lists"), "")

    def test_policy_uses_assessed_state_and_real_conflicts(self):
        student, agent = StudentCognitiveModel("alice"), CodingAgent()
        self.assertEqual(agent.choose_action(student, "Strings").difficulty, "easy")
        state = student.get_concept("Strings")
        state.attempts, state.mastery, state.confidence = 3, .6, .7
        self.assertEqual(agent.choose_action(student, "Strings").difficulty, "medium")
        state.mastery = .9
        self.assertEqual(agent.choose_action(student, "Strings").difficulty, "hard")
        self.assertEqual(agent.choose_action(student, "Strings", True).action_type, "diagnostic_coding")
        engine = CognitiveEngine()
        engine.misconception_manager.record_support(student, "Strings", "Controlled hypothesis", "coding")
        self.assertEqual(agent.choose_action(student, "Strings").difficulty, "easy")


class EvaluationGuardrailTests(unittest.TestCase):
    def evaluator(self):
        # Skip provider construction. This fake response tests the real evaluator
        # against actual static analysis and subprocess execution with no network.
        evaluator = CodingEvaluator.__new__(CodingEvaluator)
        evaluator.static_analyzer = CodingStaticAnalyzer()
        evaluator.code_runner = ControlledCodeRunner()
        evaluator.model_name = "offline-fixture"
        evaluator.client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **kwargs:
            SimpleNamespace(text=json.dumps(dict(performance=1, confidence=.9, feedback="Controlled semantic response",
                                                detected_misconceptions=[])))))
        return evaluator

    def test_failing_case_cannot_be_overruled_by_semantic_score(self):
        exercise = get_verified_exercise("Arrays")
        result = self.evaluator().evaluate(CodingSubmission("alice", exercise.task,
            "def find_max(nums):\n    return max(0, *nums)"), exercise.test_cases)
        self.assertFalse(result.is_correct)
        self.assertAlmostEqual(result.performance, 2 / 3)

    def test_full_pass_preserves_semantic_evaluation(self):
        exercise = get_verified_exercise("Strings")
        result = self.evaluator().evaluate(CodingSubmission("alice", exercise.task,
            SOLUTIONS[("Strings", "easy")]), exercise.test_cases)
        self.assertTrue(result.is_correct)
        self.assertEqual(result.performance, 1)

    def test_timeout_counts_unrun_tests_in_denominator(self):
        exercise = get_verified_exercise("Strings")
        evaluator = self.evaluator()
        evaluator.code_runner = ControlledCodeRunner(timeout_seconds=.5)
        result = evaluator.evaluate(CodingSubmission("alice", exercise.task,
            "def count_vowels(text):\n    while True: pass"), exercise.test_cases)
        self.assertFalse(result.is_correct)
        self.assertEqual(result.performance, 0)
        self.assertEqual(len(result.test_results), 1)
        self.assertEqual(result.test_results[0].error, "TIMEOUT")


if __name__ == "__main__":
    unittest.main()
