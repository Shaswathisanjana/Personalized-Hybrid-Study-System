from pathlib import Path

page = Path("app/research_agent/streamlit_page.py").read_text(
    encoding="utf-8-sig"
)

checks = {
    "Future import remains first": (
        page.lstrip().startswith(
            "from __future__ import annotations"
        )
    ),
    "Diagnostic import occurs exactly once": (
        page.count(
            "import display_research_diagnostic"
        ) == 1
    ),
    "Diagnostic interface is called exactly once": (
        page.count(
            "                display_research_diagnostic("
        ) == 1
    ),
    "Ordinary research assessment remains connected": (
        "            display_research_assessment(" in page
    ),
    "Real CACM conflict check is present": (
        "orchestrator.cognitive_engine.has_conflict(" in page
    ),
    "Completed diagnostic feedback is supported": (
        'st.session_state.get("research_diagnostic_outcome")'
        in page
    ),
}

for description, passed in checks.items():
    print(
        f"{'PASS' if passed else 'FAIL'}: {description}"
    )

if not all(checks.values()):
    raise SystemExit(
        "Integration verification failed. Do not proceed."
    )

compile(
    page,
    "app/research_agent/streamlit_page.py",
    "exec",
)

print()
print("ALL STEP 99 INTEGRATION CHECKS PASSED.")
