from app.cognitive.models import StudentCognitiveModel
from app.coding_agent.models import CodingTask
from app.coding_agent.adaptive_hint_coordinator import (
    MisconceptionAwareHintCoordinator,
)


def make_task(concept):
    return CodingTask(
        concept_name=concept,
        title=f"{concept} Practice",
        description=f"Practice {concept}.",
        difficulty="easy",
    )


student = StudentCognitiveModel(user_id="adaptive_hint_student")
coordinator = MisconceptionAwareHintCoordinator()

recursion_task = make_task("Recursion")

incorrect_code = (
    "def factorial(n):\n"
    "    return n * factorial(n - 1)\n"
)

# TEST 1: Incorrect recursion receives targeted guidance.
result1 = coordinator.get_next_hint(
    task=recursion_task,
    code=incorrect_code,
    session_id="recursion_session",
)

assert result1.hint.level == 1
assert result1.is_targeted is True
assert result1.detected_issue is not None
assert result1.detected_issue.code == "possible_missing_base_case"
assert result1.hint.reveals_solution is False

print("PASS: Missing base case receives a targeted hint")
print("      Hint:", result1.hint.message)

# TEST 2: Subsequent hints continue progressing.
result2 = coordinator.get_next_hint(
    task=recursion_task,
    code=incorrect_code,
    session_id="recursion_session",
)

result3 = coordinator.get_next_hint(
    task=recursion_task,
    code=incorrect_code,
    session_id="recursion_session",
)

assert result2.hint.level == 2
assert result3.hint.level == 3

print("PASS: Progressive hints advance to Levels 2 and 3")

# TEST 3: Correct recursion receives ordinary guidance.
correct_code = (
    "def factorial(n):\n"
    "    if n == 0:\n"
    "        return 1\n"
    "    return n * factorial(n - 1)\n"
)

correct_result = coordinator.get_next_hint(
    task=recursion_task,
    code=correct_code,
    session_id="correct_recursion_session",
)

assert correct_result.is_targeted is False
assert correct_result.detected_issue is None
assert correct_result.hint.level == 1

print("PASS: Correct recursion is not incorrectly flagged")

# TEST 4: Prime-number mistake receives targeted guidance.
prime_result = coordinator.get_next_hint(
    task=make_task("Prime Numbers"),
    code=(
        "def is_prime(n):\n"
        "    if n == 1:\n"
        "        return True\n"
        "    return False\n"
    ),
    session_id="prime_session",
)

assert prime_result.is_targeted is True
assert prime_result.detected_issue.code == "one_marked_as_prime"

print("PASS: Prime-number mistake receives targeted guidance")

# TEST 5: Array mistake receives targeted guidance.
array_result = coordinator.get_next_hint(
    task=make_task("Arrays"),
    code=(
        "def find_max(nums):\n"
        "    maximum = 0\n"
        "    for n in nums:\n"
        "        if n > maximum:\n"
        "            maximum = n\n"
        "    return maximum\n"
    ),
    session_id="array_session",
)

assert array_result.is_targeted is True
assert array_result.detected_issue.code == "zero_initialized_maximum"

print("PASS: Array mistake receives targeted guidance")

# TEST 6: Invalid syntax must not create a fabricated finding.
syntax_result = coordinator.get_next_hint(
    task=recursion_task,
    code="def factorial(:\n    pass\n",
    session_id="syntax_session",
)

assert syntax_result.is_targeted is False
assert syntax_result.detected_issue is None

print("PASS: Invalid syntax does not fabricate a misconception")

# TEST 7: Hint requests must not update CACM.
for concept in ("Recursion", "Prime Numbers", "Arrays"):
    state = student.get_concept(concept)

    assert state.mastery == 0.5
    assert state.confidence == 0.0
    assert state.attempts == 0

print("PASS: CACM mastery, confidence and attempts unchanged")

# TEST 8: Reset must restart progression.
coordinator.reset_hints(
    task=recursion_task,
    session_id="recursion_session",
)

reset_result = coordinator.get_next_hint(
    task=recursion_task,
    code=incorrect_code,
    session_id="recursion_session",
)

assert reset_result.hint.level == 1

print("PASS: Reset restarts hint progression")

print()
print("ALL ADAPTIVE HINT TESTS PASSED")
