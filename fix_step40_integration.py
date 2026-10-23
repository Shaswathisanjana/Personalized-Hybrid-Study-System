from pathlib import Path
import re
import shutil
import subprocess
import sys

path = Path("app/learning_agent/resources/resource_recommender.py")
original = path.read_text(encoding="utf-8-sig")

print("\n========== CURRENT STATUS ==========")

import_name = "OfficialDocumentationRetriever"

if import_name in original:
    print("Official documentation already appears in the file.")
    print("Stopping without making further changes.")
    sys.exit(0)

# Find the existing Wikipedia retriever entry regardless of indentation.
pattern = r"(?m)^([ \t]*)WikipediaResourceRetriever\(\),[ \t]*$"
matches = list(re.finditer(pattern, original))

if len(matches) != 1:
    raise RuntimeError(
        f"Expected exactly one Wikipedia retriever entry; found {len(matches)}. "
        "No changes made."
    )

import_anchor = (
    "from app.learning_agent.resources.relevance_guard import ("
)

if original.count(import_anchor) != 1:
    raise RuntimeError(
        "Could not uniquely identify the import location. No changes made."
    )

backup = path.with_name(path.name + ".step40.bak")
shutil.copy2(path, backup)

match = matches[0]
indent = match.group(1)

new_entry = (
    match.group(0)
    + "\n"
    + indent
    + "OfficialDocumentationRetriever(),"
)

updated = (
    original[:match.start()]
    + new_entry
    + original[match.end():]
)

new_import = (
    "from app.learning_agent.resources.official_docs_retriever import (\n"
    "    OfficialDocumentationRetriever,\n"
    ")\n\n"
)

updated = updated.replace(
    import_anchor,
    new_import + import_anchor,
    1,
)

path.write_text(updated, encoding="utf-8")

print("\n========== SYNTAX CHECK ==========")

result = subprocess.run(
    [sys.executable, "-m", "py_compile", str(path)],
    check=False,
)

if result.returncode != 0:
    shutil.copy2(backup, path)
    raise RuntimeError(
        "Syntax check failed. Original file restored."
    )

print("Syntax check passed.")

print("\n========== INTEGRATION CHECK ==========")

for number, line in enumerate(updated.splitlines(), start=1):
    if import_name in line:
        print(f"Line {number}: {line.strip()}")

assert updated.count(import_name) == 2, (
    "Expected one import and one retriever registration."
)

print("\nSTEP 40 INTEGRATION VERIFIED")
