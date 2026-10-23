from pathlib import Path
import shutil

path = Path("review_ui.py")
backup = Path("review_ui.py.step75.bak")

source = path.read_text(encoding="utf-8-sig")

anchor = '''    with st.expander("Browse Learning Topics", expanded=False):
'''

dashboard = '''    # =====================================================
    # STUDENT LEARNING PROGRESS
    # =====================================================

    with st.expander("My Learning Progress", expanded=False):

        progress_tracker = (
            st.session_state.learning_progress_tracker
        )

        progress_records = progress_tracker.list_progress(
            student.user_id
        )

        if not progress_records:
            st.info(
                "No learning activity recorded yet. "
                "Start a learning topic to see your progress here."
            )

        else:
            total_topics = len(progress_records)

            completed_sessions = sum(
                record.completed_practice_sessions
                for record in progress_records
            )

            answered_questions = sum(
                record.total_practice_questions
                for record in progress_records
            )

            metric_a, metric_b, metric_c = st.columns(3)

            metric_a.metric(
                "Topics Started",
                total_topics,
            )

            metric_b.metric(
                "Practice Sessions Completed",
                completed_sessions,
            )

            metric_c.metric(
                "Questions Answered",
                answered_questions,
            )

            st.caption(
                "Practice completion records activity, "
                "not proof of topic mastery. Cognitive estimates "
                "come from the existing CACM model."
            )

            for record in progress_records:

                snapshot = progress_tracker.snapshot(
                    student,
                    record.topic_name,
                )

                if snapshot is None:
                    continue

                st.divider()

                st.markdown(
                    f"#### {snapshot.topic_name}"
                )

                status_label = (
                    "Practice completed"
                    if snapshot.status == "practice_completed"
                    else "Started"
                )

                st.write(
                    f"**Activity status:** {status_label}"
                )

                st.write(
                    "**Started:** "
                    + snapshot.started_at.strftime(
                        "%d %b %Y, %I:%M %p"
                    )
                )

                st.write(
                    "**Last activity:** "
                    + snapshot.last_activity_at.strftime(
                        "%d %b %Y, %I:%M %p"
                    )
                )

                activity_a, activity_b = st.columns(2)

                activity_a.metric(
                    "Completed Practice Sessions",
                    snapshot.completed_practice_sessions,
                )

                activity_b.metric(
                    "Practice Questions Answered",
                    snapshot.total_practice_questions,
                )

                if (
                    snapshot.mastery is None
                    or snapshot.confidence is None
                ):
                    st.caption(
                        "No existing CACM estimate is available "
                        "for this topic yet."
                    )

                else:
                    cognitive_a, cognitive_b, cognitive_c = (
                        st.columns(3)
                    )

                    cognitive_a.metric(
                        "CACM Mastery Estimate",
                        f"{snapshot.mastery:.0%}",
                    )

                    cognitive_b.metric(
                        "CACM Confidence Estimate",
                        f"{snapshot.confidence:.0%}",
                    )

                    cognitive_c.metric(
                        "CACM Evidence Attempts",
                        snapshot.cognitive_attempts,
                    )

'''

assert source.count(anchor) == 1, (
    "Student View topic browser anchor not found exactly once."
)

assert 'with st.expander("My Learning Progress"' not in source, (
    "Learning progress dashboard appears to exist already."
)

updated = source.replace(
    anchor,
    dashboard + anchor,
    1,
)

shutil.copy2(path, backup)
path.write_text(updated, encoding="utf-8")

print("Backup created:", backup)
print("My Learning Progress dashboard installed.")
