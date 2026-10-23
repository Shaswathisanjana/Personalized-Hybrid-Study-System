from pathlib import Path

files = {
    "STUDENT COGNITIVE MODEL": (
        "app/cognitive/models.py",
        1,
        260,
    ),
    "LEARNING RUNTIME": (
        "app/learning_agent/runtime.py",
        1,
        300,
    ),
    "PRACTICE SESSION": (
        "app/learning_agent/practice_session.py",
        1,
        190,
    ),
    "COGNITIVE STATE DISPLAY": (
        "review_ui.py",
        300,
        345,
    ),
}

for heading, (filename, start, end) in files.items():
    print(f"\n========== {heading} ==========")

    path = Path(filename)

    if not path.exists():
        print(f"FILE NOT FOUND: {filename}")
        continue

    lines = path.read_text(
        encoding="utf-8-sig"
    ).splitlines()

    for number in range(start, min(end, len(lines)) + 1):
        print(f"{number:4}: {lines[number - 1]}")

print("\n========== EXISTING PROGRESS REFERENCES ==========")

for filename in (
    "app/cognitive/models.py",
    "app/learning_agent/runtime.py",
    "review_ui.py",
):
    path = Path(filename)

    if not path.exists():
        continue

    lines = path.read_text(
        encoding="utf-8-sig"
    ).splitlines()

    for number, line in enumerate(lines, start=1):
        if any(
            term in line.lower()
            for term in (
                "progress",
                "completed",
                "mastery",
                "confidence",
                "history",
            )
        ):
            print(f"{filename}:{number}: {line.strip()}")
