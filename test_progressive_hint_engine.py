from app.cognitive.models import StudentCognitiveModel
from app.coding_agent.models import CodingTask
from app.coding_agent.progressive_hint_engine import ProgressiveHintEngine


student = StudentCognitiveModel(user_id="hint_test_student")

task = CodingTask(
    concept_name="Recursion",
    title="Factorial Using Recursion",
    description="Write a recursive factorial function.",
    difficulty="easy",
    misconception_targets=["missing_base_case"],
)

engine = ProgressiveHintEngine()

state = student.get_concept("Recursion")
mastery_before = state.mastery
confidence_before = state.confidence
attempts_before = state.attempts

session_id = "hint_test_session"

# Request three progressively more specific hints.
for expected_level in (1, 2, 3):
    hint = engine.get_next_hint(
        task=task,
        session_id=session_id,
        misconception="missing_base_case",
    )

    assert hint.level == expected_level
    assert hint.reveals_solution is False
    assert hint.misconception_target == "missing_base_case"

    print(f"PASS: Level {hint.level} - {hint.title}")
    print(f"      {hint.message}")

# Further requests must not advance beyond Level 3.
last_hint = engine.get_next_hint(
    task=task,
    session_id=session_id,
)

assert last_hint.level == 3
print("PASS: Hint progression stops at Level 3")

# An unsupported misconception must not be accepted as a task target.
unknown_hint = engine.get_hint(
    task=task,
    level=1,
    misconception="unverified_misconception",
)

assert unknown_hint.misconception_target == ""
print("PASS: Unsupported misconception label rejected")

# Requesting hints must not count as an assessment.
state_after = student.get_concept("Recursion")

assert state_after.mastery == mastery_before
assert state_after.confidence == confidence_before
assert state_after.attempts == attempts_before

print("PASS: CACM mastery unchanged")
print("PASS: CACM confidence unchanged")
print("PASS: CACM attempts unchanged")

# Resetting must restart the progression.
engine.reset_hints(task, session_id)

reset_hint = engine.get_next_hint(
    task=task,
    session_id=session_id,
)

assert reset_hint.level == 1
print("PASS: Reset returns progression to Level 1")

print()
print("ALL PROGRESSIVE HINT TESTS PASSED")
