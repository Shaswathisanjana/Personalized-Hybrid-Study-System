from pathlib import Path

lines = Path("review_ui.py").read_text(
    encoding="utf-8-sig"
).splitlines()

print("\n========== STUDENT VIEW SUBMISSION FLOW ==========")

for number in range(1550, min(1810, len(lines)) + 1):
    print(f"{number:4}: {lines[number - 1]}")

print("\n========== QUERY STATE REFERENCES ==========")

for number, line in enumerate(lines, start=1):
    if any(
        term in line
        for term in (
            "last_query",
            "orchestrator.run(",
            "orchestrator.process(",
            "query=query",
        )
    ):
        print(f"{number:4}: {line}")
