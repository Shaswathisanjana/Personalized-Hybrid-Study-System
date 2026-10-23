from pathlib import Path

path = Path(".gitignore")
content = path.read_text(encoding="utf-8-sig")

section = """
# CACM Research Agent - generated and temporary files
data/research_reports/
*.bak
"""

if "# CACM Research Agent - generated and temporary files" not in content:
    updated = content.rstrip() + "\n\n" + section.lstrip()
    path.write_text(updated, encoding="utf-8")
    print("SUCCESS: Research Agent ignore rules added.")
else:
    print("Research Agent ignore rules already exist.")

print("\nCurrent ignore checks:")
