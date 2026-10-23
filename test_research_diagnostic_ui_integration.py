from pathlib import Path

import ast

page = Path("app/research_agent/streamlit_page.py").read_text(
    encoding="utf-8-sig"
)

tree = ast.parse(page)
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
        sum(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "display_research_diagnostic" for node in ast.walk(tree)) == 1
    ),
    "Ordinary research assessment remains connected": (
        "            display_research_assessment(" in page
    ),
    "Real CACM conflict check is present": (
        "orchestrator.cognitive_engine.has_conflict(" in page
    ),
    "Completed diagnostic feedback is supported": (
        any(isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get" and ast.unparse(node.func.value) == "st.session_state"
            and node.args and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "research_diagnostic_outcome" for node in ast.walk(tree))
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
