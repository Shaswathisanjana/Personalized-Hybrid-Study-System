from pathlib import Path

sections = {
    "app/learning_agent/progress_tracker.py": [
        (1, 260),
    ],
    "review_ui.py": [
        (1590, 1630),
        (1730, 1790),
        (1890, 1950),
    ],
}

for filename, ranges in sections.items():
    lines = Path(filename).read_text(
        encoding="utf-8-sig"
    ).splitlines()

    for start, end in ranges:
        print(
            f"\n========== {filename}: "
            f"{start}-{end} =========="
        )

        for number in range(
            start,
            min(end, len(lines)) + 1,
        ):
            print(f"{number:4}: {lines[number - 1]}")

print("\nSTEP 74 INSPECTION COMPLETE")
