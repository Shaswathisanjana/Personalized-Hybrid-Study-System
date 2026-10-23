from pathlib import Path
import py_compile
import shutil

path = Path("review_ui.py")
backup = Path("review_ui_before_advanced_research.py.bak")

source = path.read_text(encoding="utf-8-sig")

old_navigation = '''            "Student View",
            "CACM Professor Demo",
            "System Architecture",'''

new_navigation = '''            "Student View",
            "Advanced Research Agent",
            "CACM Professor Demo",
            "System Architecture",'''

old_route = 'elif page == "CACM Professor Demo":'

new_route = '''elif page == "Advanced Research Agent":

    from app.research_agent.streamlit_page import (
        display_advanced_research_page,
    )

    display_advanced_research_page(
        student=student,
        orchestrator=orchestrator,
    )


elif page == "CACM Professor Demo":'''

if new_navigation in source and new_route in source:
    print("Advanced Research Agent is already integrated.")
elif (
    source.count(old_navigation) != 1
    or source.count(old_route) != 1
):
    raise RuntimeError(
        "Expected integration markers were not found exactly once. "
        "review_ui.py has not been modified."
    )
else:
    shutil.copy2(path, backup)

    updated = source.replace(
        old_navigation,
        new_navigation,
        1,
    ).replace(
        old_route,
        new_route,
        1,
    )

    try:
        path.write_text(updated, encoding="utf-8")
        py_compile.compile(
            str(path),
            doraise=True,
        )
    except Exception:
        shutil.copy2(backup, path)
        print("Integration failed. Original review_ui.py restored.")
        raise

    print("SUCCESS: Advanced Research Agent navigation integrated.")
    print("Backup:", backup)

py_compile.compile(
    "app/research_agent/streamlit_page.py",
    doraise=True,
)

py_compile.compile(
    "review_ui.py",
    doraise=True,
)

print("SUCCESS: Both Python syntax checks passed.")
