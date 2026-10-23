from pathlib import Path

path = Path("app/research_agent/streamlit_assessment.py")
original = path.read_text(encoding="utf-8-sig")

old = 'if "research_assessment_service" not in st.session_state:'
new = 'if st.session_state.get("research_assessment_service") is None:'

if original.count(old) != 1:
    raise RuntimeError(
        "Expected initialization line was not found exactly once. "
        "No changes were made."
    )

backup = Path(
    "app/research_agent/streamlit_assessment_before_fix.py.bak"
)
backup.write_text(original, encoding="utf-8")

path.write_text(
    original.replace(old, new, 1),
    encoding="utf-8",
)

print("PASS: Assessment service initialization corrected.")
print("PASS: Backup created.")
