from pathlib import Path

sections = {
    "LEARNING RUNTIME - SESSION COMPLETION": (
        "app/learning_agent/runtime.py",
        740,
        980,
    ),
    "STREAMLIT - ADAPTIVE PRACTICE": (
        "review_ui.py",
        555,
        880,
    ),
    "STREAMLIT - PRACTICE RESULTS": (
        "review_ui.py",
        880,
        1100,
    ),
}

for heading, (filename, start, end) in sections.items():
    print(f"\n========== {heading} ==========")

    path = Path(filename)
    lines = path.read_text(
        encoding="utf-8-sig"
    ).splitlines()

    for number in range(start, min(end, len(lines)) + 1):
        print(f"{number:4}: {lines[number - 1]}")

print("\n========== COMPLETION REFERENCES ==========")

for filename in (
    "app/learning_agent/runtime.py",
    "review_ui.py",
):
    lines = Path(filename).read_text(
        encoding="utf-8-sig"
    ).splitlines()

    for number, line in enumerate(lines, start=1):
        if any(
            term in line
            for term in (
                "practice_summary",
                "outcome.summary",
                "session.is_complete",
                "submit_practice_session_answer",
                "start_practice_session",
            )
        ):
            print(f"{filename}:{number}: {line.strip()}")
