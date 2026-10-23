from pathlib import Path

path = Path("app/research_agent/streamlit_page.py")
source = path.read_text(encoding="utf-8-sig")

old_import = """from app.research_agent.streamlit_assessment import (
    display_research_assessment,
)
"""

new_import = """from app.research_agent.streamlit_assessment import (
    display_research_assessment,
)
from app.research_agent.streamlit_decisions import (
    display_research_decisions,
)
"""

old_assignment = """                st.session_state.advanced_research_action = (
                    outcome.action
                )
"""

new_assignment = """                st.session_state.advanced_research_action = (
                    outcome.action
                )

                st.session_state.advanced_research_plan = (
                    outcome.plan
                )
"""

old_display = """        display_advanced_research_results(result)
"""

new_display = """        plan = st.session_state.get(
            "advanced_research_plan"
        )

        if plan is not None:
            display_research_decisions(
                plan=plan,
                research=result,
            )

        display_advanced_research_results(result)
"""

changes = [
    (old_import, new_import, "dashboard import"),
    (old_assignment, new_assignment, "research plan storage"),
    (old_display, new_display, "dashboard display"),
]

for old, new, label in changes:
    count = source.count(old)

    if count != 1:
        raise RuntimeError(
            f"Expected exactly one {label} location; "
            f"found {count}. No changes were written."
        )

for old, new, label in changes:
    source = source.replace(old, new, 1)

compile(source, str(path), "exec")

backup = Path(
    "app/research_agent/streamlit_page_before_dashboard.bak"
)

backup.write_text(
    path.read_text(encoding="utf-8-sig"),
    encoding="utf-8",
)

path.write_text(source, encoding="utf-8")

print("PASS: Decision Dashboard imported.")
print("PASS: Research plan stored in Streamlit session.")
print("PASS: Dashboard displayed above research results.")
print("PASS: Existing comprehension assessment preserved.")
print("PASS: Original file backed up.")
