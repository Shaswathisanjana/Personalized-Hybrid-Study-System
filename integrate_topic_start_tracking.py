from pathlib import Path
import shutil

path = Path("review_ui.py")
backup = Path("review_ui.py.step73.bak")

source = path.read_text(encoding="utf-8-sig")

old = '''                    st.session_state.last_result = (
                        result
                    )

                    st.rerun()
'''

new = '''                    st.session_state.last_result = (
                        result
                    )

                    # Record a learning topic only when the
                    # Learning Agent successfully produced
                    # its response. Merely browsing a topic
                    # does not count as starting learning.
                    learning_succeeded = any(
                        agent_result.agent == "learning"
                        and agent_result.success
                        for agent_result in result.agent_results
                    )

                    if learning_succeeded:
                        st.session_state.learning_progress_tracker.start_topic(
                            user_id=student.user_id,
                            topic_name=result.route.concept,
                        )

                    st.rerun()
'''

assert source.count(old) == 1, (
    "Expected successful-result block not found exactly once."
)

assert "learning_succeeded = any(" not in source, (
    "Topic-start tracking appears to be installed already."
)

updated = source.replace(old, new, 1)

shutil.copy2(path, backup)
path.write_text(updated, encoding="utf-8")

print("Backup created:", backup)
print("Successful Learning Agent topic tracking installed.")
