from pathlib import Path

path = Path("app/research_agent/streamlit_page.py")
source = path.read_text(encoding="utf-8-sig")

import_line = (
    "from app.research_agent.streamlit_decisions "
    "import display_research_decisions\n"
)

if import_line not in source:
    source = import_line + source

old = (
    "st.session_state.advanced_research_action = outcome.action"
)

new = (
    "st.session_state.advanced_research_action = outcome.action\n"
    "            st.session_state.advanced_research_plan = outcome.plan"
)

if source.count(old) != 1:
    raise RuntimeError(
        "Could not uniquely locate the research action assignment. "
        "No changes were written."
    )

source = source.replace(old, new, 1)

old_display = "display_advanced_research_results(result)"

new_display = """plan = st.session_state.get("advanced_research_plan")

        if plan is not None:
            display_research_decisions(
                plan=plan,
                research=result,
            )

        display_advanced_research_results(result)"""

if source.count(old_display) != 1:
    raise RuntimeError(
        "Could not uniquely locate the research results display. "
        "No changes were written."
    )

source = source.replace(old_display, new_display, 1)

compile(source, str(path), "exec")

backup = path.with_suffix(".py.bak")
backup.write_text(
    path.read_text(encoding="utf-8-sig"),
    encoding="utf-8",
)

path.write_text(source, encoding="utf-8")

print("PASS: Decision Dashboard connected to Streamlit.")
print("PASS: Research results and assessment integration preserved.")
print("PASS: Original Streamlit page backed up.")
