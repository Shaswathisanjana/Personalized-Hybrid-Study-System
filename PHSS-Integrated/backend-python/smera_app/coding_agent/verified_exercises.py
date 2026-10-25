from dataclasses import dataclass, field

from smera_app.coding_agent.models import CodingTask
from smera_app.coding_agent.code_runner import BehavioralTestCase


@dataclass
class VerifiedCodingExercise:
    task: CodingTask
    test_cases: list[BehavioralTestCase] = field(default_factory=list)


def get_verified_exercise(
    concept_name: str,
    difficulty: str = "easy",
) -> VerifiedCodingExercise:

    concept = concept_name.strip().lower()

    if concept == "recursion":
        return VerifiedCodingExercise(
            task=CodingTask(
                concept_name="Recursion",
                title="Factorial Using Recursion",
                description=(
                    "Write a Python function factorial(n) that "
                    "returns the factorial of a non-negative integer "
                    "using recursion. For example, factorial(4) = 24."
                ),
                difficulty=difficulty,
                starter_code=(
                    "def factorial(n):\n"
                    "    # Write your recursive solution here\n"
                    "    pass\n"
                ),
                expected_behavior=(
                    "factorial(0) = 1, factorial(4) = 24"
                ),
                misconception_targets=[
                    "Missing recursive base case",
                    "Incorrect recursive step",
                ],
            ),
            test_cases=[
                BehavioralTestCase(
                    test_name="Zero factorial",
                    function_name="factorial",
                    args=[0],
                    expected_output=1,
                ),
                BehavioralTestCase(
                    test_name="Factorial four",
                    function_name="factorial",
                    args=[4],
                    expected_output=24,
                ),
                BehavioralTestCase(
                    test_name="Factorial six",
                    function_name="factorial",
                    args=[6],
                    expected_output=720,
                ),
            ],
        )

    if concept in {"prime", "prime numbers", "prime number"}:
        return VerifiedCodingExercise(
            task=CodingTask(
                concept_name="Prime Numbers",
                title="Check Prime Number",
                description=(
                    "Write a function is_prime(n) that returns True "
                    "when n is prime and False otherwise. "
                    "Numbers less than 2 are not prime."
                ),
                difficulty=difficulty,
                starter_code=(
                    "def is_prime(n):\n"
                    "    # Write your solution here\n"
                    "    pass\n"
                ),
                expected_behavior=(
                    "is_prime(2) = True, is_prime(9) = False"
                ),
            ),
            test_cases=[
                BehavioralTestCase(
                    test_name="Smallest prime",
                    function_name="is_prime",
                    args=[2],
                    expected_output=True,
                ),
                BehavioralTestCase(
                    test_name="Composite number",
                    function_name="is_prime",
                    args=[9],
                    expected_output=False,
                ),
                BehavioralTestCase(
                    test_name="Number below two",
                    function_name="is_prime",
                    args=[1],
                    expected_output=False,
                ),
                BehavioralTestCase(
                    test_name="Larger prime",
                    function_name="is_prime",
                    args=[29],
                    expected_output=True,
                ),
            ],
        )

    if concept in {"arrays", "array"}:
        return VerifiedCodingExercise(
            task=CodingTask(
                concept_name="Arrays",
                title="Find Maximum Element",
                description=(
                    "Write a function find_max(nums) that returns "
                    "the largest element in a non-empty list. "
                    "Do not use Python's built-in max() function."
                ),
                difficulty=difficulty,
                starter_code=(
                    "def find_max(nums):\n"
                    "    # Write your solution here\n"
                    "    pass\n"
                ),
                expected_behavior=(
                    "find_max([3, 1, 5, 2]) = 5"
                ),
            ),
            test_cases=[
                BehavioralTestCase(
                    test_name="Mixed positive values",
                    function_name="find_max",
                    args=[[3, 1, 5, 2]],
                    expected_output=5,
                ),
                BehavioralTestCase(
                    test_name="Negative values",
                    function_name="find_max",
                    args=[[-8, -2, -10]],
                    expected_output=-2,
                ),
                BehavioralTestCase(
                    test_name="Single element",
                    function_name="find_max",
                    args=[[7]],
                    expected_output=7,
                ),
            ],
        )

    raise ValueError(
        f"No verified coding exercise available for: {concept_name}"
    )
