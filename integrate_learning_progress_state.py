from pathlib import Path
import shutil

path = Path("review_ui.py")
backup = Path("review_ui.py.step69.bak")

source = path.read_text(encoding="utf-8-sig")

old_import = (
    "from app.learning_agent.topic_bank import LearningTopicBank\n"
)

new_import = (
    "from app.learning_agent.topic_bank import LearningTopicBank\n"
    "from app.learning_agent.progress_tracker import LearningProgressTracker\n"
)

old_initialization = '''if "last_result" not in st.session_state:
    st.session_state.last_result = None
'''

new_initialization = '''if "learning_progress_tracker" not in st.session_state:
    st.session_state.learning_progress_tracker = (
        LearningProgressTracker()
    )

if "last_result" not in st.session_state:
    st.session_state.last_result = None
'''

old_reset = '''    st.session_state.orchestrator = OrchestratorRuntime()

    st.session_state.last_result = None
'''

new_reset = '''    st.session_state.orchestrator = OrchestratorRuntime()

    # A full reset clears learning activity history too.
    # Ordinary practice resets must preserve this tracker.
    st.session_state.learning_progress_tracker = (
        LearningProgressTracker()
    )

    st.session_state.last_result = None
'''

assert source.count(old_import) == 1, (
    "LearningTopicBank import not found exactly once."
)

assert source.count(old_initialization) == 1, (
    "Session initialization anchor not found exactly once."
)

assert source.count(old_reset) == 1, (
    "Full reset anchor not found exactly once."
)

assert "learning_progress_tracker" not in source, (
    "Progress tracker appears to be integrated already."
)

updated = source.replace(
    old_import,
    new_import,
    1,
).replace(
    old_initialization,
    new_initialization,
    1,
).replace(
    old_reset,
    new_reset,
    1,
)

shutil.copy2(path, backup)
path.write_text(updated, encoding="utf-8")

print("Backup created:", backup)
print("Progress tracker initialized in Streamlit.")
print("Full reset updated.")
