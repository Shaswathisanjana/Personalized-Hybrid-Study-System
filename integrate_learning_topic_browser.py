from pathlib import Path
import shutil

path = Path("review_ui.py")
backup = Path("review_ui.py.step61.bak")

source = path.read_text(encoding="utf-8-sig")

import_anchor = (
    "from app.orchestrator.orchestrator_runtime "
    "import OrchestratorRuntime"
)

assert source.count(import_anchor) == 1, (
    "Expected orchestrator import not found exactly once."
)

assert "from app.learning_agent.topic_bank import LearningTopicBank" not in source
assert "learning_request_input" not in source
assert "learning_topic_browser_category" not in source

old_input = '''    query = st.text_input(
        "What would you like help with?",
        placeholder=(
            "Example: Teach me recursion in Python "
            "from basics"
        ),
    )
'''

assert source.count(old_input) == 1, (
    "Expected original student query input not found exactly once."
)

new_import = (
    import_anchor
    + "\nfrom app.learning_agent.topic_bank import LearningTopicBank"
)

source = source.replace(
    import_anchor,
    new_import,
    1,
)

new_input = '''    with st.expander("Browse Learning Topics", expanded=False):
        topic_bank = LearningTopicBank()

        st.caption(
            "Choose a structured topic or enter your own. "
            "This prepares a request for the existing "
            "multi-agent assistant."
        )

        selected_category = st.selectbox(
            "Learning category",
            topic_bank.categories() + ["Custom Topic"],
            key="learning_topic_browser_category",
        )

        if selected_category == "Custom Topic":
            selected_topic_name = st.text_input(
                "Enter your own topic",
                placeholder="Example: Quantum Computing",
                key="learning_topic_browser_custom",
            ).strip()

            if selected_topic_name:
                st.info(
                    "Custom topics are supported. "
                    "Structured prerequisite guidance "
                    "is not available for this topic yet."
                )

        else:
            category_topics = topic_bank.by_category(
                selected_category
            )

            selected_topic_name = st.selectbox(
                "Choose a topic",
                [topic.name for topic in category_topics],
                key="learning_topic_browser_topic",
            )

            selected_topic = topic_bank.get(
                selected_topic_name
            )

            st.caption(
                f"Suggested starting difficulty: "
                f"{selected_topic.difficulty.title()}"
            )

            prerequisites = topic_bank.prerequisites_for(
                selected_topic_name
            )

            if prerequisites:
                st.info(
                    "Suggested prerequisites: "
                    + ", ".join(
                        topic.name for topic in prerequisites
                    )
                )
            else:
                st.success(
                    "No prerequisites are listed for this topic."
                )

        if st.button(
            "Use This Learning Topic",
            key="learning_topic_browser_use",
            disabled=not bool(selected_topic_name),
        ):
            st.session_state["learning_request_input"] = (
                f"Teach me {selected_topic_name} "
                "step by step, starting from my current level."
            )
            st.rerun()

    query = st.text_input(
        "What would you like help with?",
        placeholder=(
            "Example: Teach me recursion in Python "
            "from basics"
        ),
        key="learning_request_input",
    )
'''

source = source.replace(
    old_input,
    new_input,
    1,
)

assert source.count("orchestrator.handle_query(") == 1
assert source.count('key="learning_request_input"') == 1
assert source.count("learning_topic_browser_use") == 1

shutil.copy2(path, backup)
path.write_text(source, encoding="utf-8")

print("Backup created:", backup)
print("Topic browser integrated.")
print("Original multi-agent submission pathway preserved.")
