from pathlib import Path

path = Path("review_ui.py")
lines = path.read_text(
    encoding="utf-8-sig"
).splitlines()

print("\n========== STUDENT VIEW AND START LEARNING ==========")

for number in range(1530, min(1740, len(lines)) + 1):
    print(f"{number:4}: {lines[number - 1]}")

print("\n========== LEARNING OUTPUT CALLS ==========")

for number, line in enumerate(lines, start=1):
    if any(
        term in line
        for term in (
            "handle_query(",
            "display_learning_output(",
            "last_result =",
            "last_query =",
            "learning_progress_tracker",
        )
    ):
        print(f"{number:4}: {line.strip()}")

print("\nSTEP 71 INSPECTION COMPLETE")
