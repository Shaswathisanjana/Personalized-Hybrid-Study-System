from pathlib import Path

files = {
    "review_ui.py": [(1730, 1910)],
    "app/orchestrator/orchestrator_runtime.py": [(1, 270)],
}

for filename, ranges in files.items():
    path = Path(filename)
    lines = path.read_text(
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

print("\nSTEP 72 INSPECTION COMPLETE")
