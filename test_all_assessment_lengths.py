from pathlib import Path
import subprocess
import sys

source = Path("test_adaptive_quiz_integration.py").read_text(
    encoding="utf-8-sig"
)

assert "max_questions=5," in source
assert "answer_pattern = [True, False, True, True, False]" in source

for count in (5, 10, 15, 20):
    print(
        f"\n========== TESTING {count} QUESTIONS ==========",
        flush=True,
    )

    script = source.replace(
        "max_questions=5,",
        f"max_questions={count},",
        1,
    )

    script = script.replace(
        "answer_pattern = [True, False, True, True, False]",
        "answer_pattern = "
        + repr(([True, False, True, True, False] * 4)[:count]),
        1,
    )

    # Update assertions and labels specific to the session length.
    script = script.replace("index < 5", f"index < {count}")
    script = script.replace("== 5", f"== {count}")
    script = script.replace("Q{index}/5", f"Q{{index}}/{count}")

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"{count}-question integration test failed."
        )

    print(
        f"PASS: Complete {count}-question adaptive session.",
        flush=True,
    )

print(
    "\nSTEP 55: ALL FOUR ASSESSMENT LENGTHS VERIFIED"
)
