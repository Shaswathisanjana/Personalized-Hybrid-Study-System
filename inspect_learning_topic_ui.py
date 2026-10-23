from pathlib import Path

path = Path("review_ui.py")
lines = path.read_text(encoding="utf-8-sig").splitlines()

print("\n========== LEARNING UI: LINES 1-180 ==========")

for number in range(1, min(180, len(lines)) + 1):
    print(f"{number:4}: {lines[number - 1]}")

print("\n========== LEARNING UI: LINES 340-560 ==========")

for number in range(340, min(560, len(lines)) + 1):
    print(f"{number:4}: {lines[number - 1]}")

print("\n========== LEARNING UI: LINES 1360-1580 ==========")

for number in range(1360, min(1580, len(lines)) + 1):
    print(f"{number:4}: {lines[number - 1]}")

print("\n========== TOPIC INPUT REFERENCES ==========")

for number, line in enumerate(lines, start=1):
    if any(
        term in line.lower()
        for term in (
            "learning topic",
            "enter a topic",
            "choose a topic",
            "learning_agent_page",
            "selected_concept",
        )
    ):
        print(f"{number:4}: {line}")
