from pathlib import Path
import shutil
import subprocess
import sys

path = Path("review_ui.py")
original = path.read_text(encoding="utf-8-sig")

old_info = '''        st.info(
            "Ready for a short 3-question adaptive "
            "practice session."
        )
'''

new_info = '''        selected_question_count = st.selectbox(
            "Number of practice questions",
            options=[5, 10, 15, 20],
            index=1,
            key="selected_practice_question_count",
            help=(
                "Questions are generated sequentially. "
                "Each answer updates CACM before the next "
                "question is generated."
            ),
        )

        st.info(
            f"Ready for a {selected_question_count}-question "
            "adaptive practice session."
        )
'''

if original.count(old_info) != 1:
    raise RuntimeError(
        "Expected exactly one original practice introduction. "
        "No changes made."
    )

if original.count("max_questions=3,") != 2:
    raise RuntimeError(
        "Expected exactly two hardcoded session limits. "
        "No changes made."
    )

# Replace the introduction and its nearby start call.
updated = original.replace(old_info, new_info, 1)

start_marker = 'key="start_adaptive_practice",'
start_position = updated.find(start_marker)

if start_position == -1:
    raise RuntimeError(
        "Could not locate Start Adaptive Practice."
    )

start_limit_position = updated.find(
    "max_questions=3,",
    start_position,
)

if start_limit_position == -1:
    raise RuntimeError(
        "Could not locate the initial session limit."
    )

updated = (
    updated[:start_limit_position]
    + "max_questions=selected_question_count,"
    + updated[start_limit_position + len("max_questions=3,"):]
)

# Practice Again uses the previously selected length.
# It does not change an active session's max_questions.
again_marker = 'key="practice_again",'
again_position = updated.find(again_marker)

if again_position == -1:
    raise RuntimeError(
        "Could not locate Practice Again."
    )

again_limit_position = updated.find(
    "max_questions=3,",
    again_position,
)

if again_limit_position == -1:
    raise RuntimeError(
        "Could not locate the Practice Again session limit."
    )

updated = (
    updated[:again_limit_position]
    + (
        'max_questions=st.session_state.get(\n'
        '                            "selected_practice_question_count",\n'
        '                            10,\n'
        '                        ),'
    )
    + updated[again_limit_position + len("max_questions=3,"):]
)

assert updated.count("max_questions=3,") == 0
assert "max_questions=selected_question_count," in updated
assert '"selected_practice_question_count"' in updated

backup = Path("review_ui.py.step49.bak")
shutil.copy2(path, backup)

path.write_text(updated, encoding="utf-8")

print("\n========== SYNTAX CHECK ==========")

result = subprocess.run(
    [sys.executable, "-m", "py_compile", str(path)],
    check=False,
)

if result.returncode != 0:
    shutil.copy2(backup, path)
    raise RuntimeError(
        "Syntax check failed. Original UI restored."
    )

print("Syntax check passed.")
print("Assessment options: 5, 10, 15, 20")
print("Default assessment length: 10")
print("Both session entry points updated.")
print("Existing CACM adaptation logic unchanged.")

print("\nSTEP 49 UI CONFIGURATION VERIFIED")
