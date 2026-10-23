from app.learning_agent.practice_session import PracticeSession


print("\n========== ADAPTIVE SESSION LENGTH TEST ==========")

for count in (5, 10, 15, 20):
    session = PracticeSession(
        user_id="assessment_length_test",
        concept_name="Python recursion",
        max_questions=count,
    )

    assert session.max_questions == count
    assert session.questions_completed == 0
    assert session.questions_remaining == count
    assert session.is_complete is False

    print(
        f"PASS: {count}-question session created; "
        f"{session.questions_remaining} questions remaining."
    )

print("\n========== DEFAULT UI CONFIGURATION ==========")

from pathlib import Path

ui = Path("review_ui.py").read_text(encoding="utf-8-sig")

assert "options=[5, 10, 15, 20]" in ui
assert 'key="selected_practice_question_count"' in ui
assert "max_questions=selected_question_count," in ui
assert "max_questions=3," not in ui

print("PASS: All four assessment lengths configured.")
print("PASS: Initial session uses the selected length.")
print("PASS: Hardcoded three-question limit removed.")

print("\n========== INVALID SESSION LENGTH ==========")

try:
    PracticeSession(
        user_id="assessment_length_test",
        concept_name="Python recursion",
        max_questions=0,
    )
except ValueError:
    print("PASS: Zero-question session rejected.")
else:
    raise AssertionError("Zero-question session was accepted.")

print("\nSTEP 50 ASSESSMENT LENGTH TEST PASSED")
