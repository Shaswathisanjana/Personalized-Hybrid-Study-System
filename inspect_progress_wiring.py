from pathlib import Path

path = Path("review_ui.py")
lines = path.read_text(
    encoding="utf-8-sig"
).splitlines()

sections = {
    "SESSION INITIALIZATION AND RESET": (1, 155),
    "PRACTICE ANSWER SUBMISSION": (1090, 1205),
    "PRACTICE AGAIN BUTTON": (345, 555),
}

for heading, (start, end) in sections.items():
    print(f"\n========== {heading} ==========")

    for number in range(start, min(end, len(lines)) + 1):
        print(f"{number:4}: {lines[number - 1]}")

print("\nSTEP 67 INSPECTION COMPLETE")
