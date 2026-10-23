from pathlib import Path

page_path = Path("app/research_agent/streamlit_page.py")
original = page_path.read_text(encoding="utf-8-sig")

backup = Path(
    "app/research_agent/streamlit_page_before_assessment.py.bak"
)

import_anchor = (
    "from app.research_agent.streamlit_results import (\n"
    "    display_advanced_research_results,\n"
    ")\n"
)

import_replacement = (
    import_anchor
    + "from app.research_agent.streamlit_assessment import (\n"
    + "    display_research_assessment,\n"
    + ")\n"
)

save_anchor = (
    "                st.session_state.advanced_research_action = (\n"
    "                    outcome.action\n"
    "                )"
)

save_replacement = (
    save_anchor
    + "\n\n"
    + "                # A new research result needs a fresh assessment.\n"
    + "                st.session_state.advanced_research_concept = (\n"
    + "                    concept_name.strip()\n"
    + "                )\n"
    + "                st.session_state.research_assessment_service = None\n"
    + "                st.session_state.research_assessment_question = None\n"
    + "                st.session_state.research_assessment_completed = False\n"
    + "                st.session_state.research_assessment_feedback = None"
)

display_anchor = (
    "        display_advanced_research_results(result)"
)

display_replacement = (
    display_anchor
    + "\n\n"
    + "        assessment_concept = st.session_state.get(\n"
    + "            'advanced_research_concept'\n"
    + "        )\n\n"
    + "        if action is not None and assessment_concept:\n"
    + "            display_research_assessment(\n"
    + "                result=result,\n"
    + "                action=action,\n"
    + "                concept_name=assessment_concept,\n"
    + "                student=student,\n"
    + "                orchestrator=orchestrator,\n"
    + "            )"
)

changes = [
    (import_anchor, import_replacement),
    (save_anchor, save_replacement),
    (display_anchor, display_replacement),
]

updated = original

for old, new in changes:
    if updated.count(old) != 1:
        raise RuntimeError(
            "Integration stopped: expected exactly one occurrence "
            f"of:\n{old}"
        )
    updated = updated.replace(old, new, 1)

backup.write_text(original, encoding="utf-8")
page_path.write_text(updated, encoding="utf-8")

print("PASS: Backup created.")
print("PASS: Assessment connected to Advanced Research page.")
