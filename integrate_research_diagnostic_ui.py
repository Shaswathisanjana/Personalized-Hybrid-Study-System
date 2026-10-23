from pathlib import Path

path = Path("app/research_agent/streamlit_page.py")
original = path.read_text(encoding="utf-8-sig")
source = original

import_line = (
    "from app.research_agent.streamlit_diagnostic "
    "import display_research_diagnostic"
)

# Insert the new import AFTER the future import.
if import_line not in source:
    future_line = "from __future__ import annotations"

    if future_line not in source:
        raise RuntimeError(
            "Expected future import not found. No changes written."
        )

    source = source.replace(
        future_line,
        future_line + "\n\n" + import_line,
        1,
    )

old = """        if action is not None and assessment_concept:
            display_research_assessment(
"""

new = """        if action is not None and assessment_concept:
            # Display the existing CACM diagnostic workflow
            # only when a real conflict exists or when
            # completed diagnostic feedback must be shown.
            if orchestrator.cognitive_engine.has_conflict(
                user_id=student.user_id,
                concept_name=assessment_concept,
            ) or (
                st.session_state.get("research_diagnostic_outcome")
                is not None
                and st.session_state.get(
                    "research_diagnostic_concept"
                ) == assessment_concept
            ):
                display_research_diagnostic(
                    concept_name=assessment_concept,
                    student=student,
                    orchestrator=orchestrator,
                )

            display_research_assessment(
"""

count = source.count(old)

if count != 1:
    raise RuntimeError(
        f"Expected one assessment integration point; found {count}. "
        "No changes were written."
    )

source = source.replace(old, new, 1)

# Validate BEFORE modifying the original file.
compile(source, str(path), "exec")

backup = Path(
    "app/research_agent/streamlit_page_before_diagnostic.bak"
)

backup.write_text(original, encoding="utf-8")

path.write_text(source, encoding="utf-8")

print("PASS: Diagnostic import placed after future import.")
print("PASS: Diagnostic interface integrated into Advanced Research.")
print("PASS: Ordinary research assessment preserved.")
print("PASS: Original page backed up.")
