from pathlib import Path
import shutil

path = Path("review_ui.py")
backup = Path("review_ui.py.step70.bak")

source = path.read_text(encoding="utf-8-sig")

old_import = '''from app.learning_agent.progress_tracker import LearningProgressTracker
'''

new_import = '''from app.learning_agent.progress_tracker import LearningProgressTracker
from uuid import uuid4
'''

old_completion = '''                if outcome.summary is not None:

                    st.session_state.practice_summary = (
                        outcome.summary
                    )
'''

new_completion = '''                if outcome.summary is not None:

                    st.session_state.practice_summary = (
                        outcome.summary
                    )

                    # A session completion is recorded only after
                    # the final answer has been evaluated by CACM.
                    # A stable ID prevents Streamlit reruns from
                    # counting the same quiz more than once.
                    tracker = (
                        st.session_state.learning_progress_tracker
                    )

                    completion_id = getattr(
                        session,
                        "_progress_completion_id",
                        None,
                    )

                    if completion_id is None:
                        completion_id = uuid4().hex
                        session._progress_completion_id = (
                            completion_id
                        )

                    tracker.complete_practice_session(
                        user_id=student.user_id,
                        topic_name=session.concept_name,
                        questions_completed=(
                            outcome.summary.questions_completed
                        ),
                        completion_id=completion_id,
                    )
'''

assert source.count(old_import) == 1, (
    "Progress tracker import not found exactly once."
)

assert source.count(old_completion) == 1, (
    "Quiz completion integration point not found exactly once."
)

assert "_progress_completion_id" not in source, (
    "Quiz completion tracking appears to be installed already."
)

updated = source.replace(
    old_import,
    new_import,
    1,
).replace(
    old_completion,
    new_completion,
    1,
)

shutil.copy2(path, backup)
path.write_text(updated, encoding="utf-8")

print("Backup created:", backup)
print("Completed quiz tracking integrated.")
