from pathlib import Path

root = Path(".")

print("\n========== EXISTING DATABASE FILES ==========")

extensions = {".db", ".sqlite", ".sqlite3"}

for path in root.rglob("*"):
    if (
        path.is_file()
        and path.suffix.lower() in extensions
        and ".venv" not in path.parts
        and ".git" not in path.parts
    ):
        print(path)

print("\n========== PERSISTENCE-RELATED PYTHON FILES ==========")

for path in root.rglob("*.py"):
    if ".venv" in path.parts or ".git" in path.parts:
        continue

    if any(
        word in path.name.lower()
        for word in (
            "storage",
            "database",
            "persistence",
            "repository",
            "progress",
        )
    ):
        print(path)

print("\n========== GITIGNORE ==========")

ignore = Path(".gitignore")

if ignore.exists():
    print(ignore.read_text(encoding="utf-8-sig"))
else:
    print("No .gitignore found.")

print("\nSTEP 79 INSPECTION COMPLETE")
