from pathlib import Path
import shutil

path = Path("app/learning_agent/progress_tracker.py")
backup = Path("app/learning_agent/progress_tracker.py.step68.bak")

source = path.read_text(encoding="utf-8-sig")

old_init = '''    def __init__(self):
        self._records: dict[
            tuple[str, str],
            TopicLearningProgress,
        ] = {}
'''

new_init = '''    def __init__(self):
        self._records: dict[
            tuple[str, str],
            TopicLearningProgress,
        ] = {}

        # Prevent duplicate completion events for the same
        # student, topic and practice session.
        self._recorded_completions: set[
            tuple[str, str, str]
        ] = set()
'''

old_completion = '''    def complete_practice_session(
        self,
        user_id: str,
        topic_name: str,
        questions_completed: int,
    ) -> TopicLearningProgress:
        if questions_completed < 1:
            raise ValueError(
                "A completed practice session must contain "
                "at least one answered question."
            )

        record = self.start_topic(
            user_id=user_id,
            topic_name=topic_name,
        )

        now = datetime.now()

        record.completed_practice_sessions += 1
        record.total_practice_questions += questions_completed
        record.last_activity_at = now

        record.events.append(
            TopicProgressEvent(
                event_type="practice_session_completed",
                recorded_at=now,
                detail=f"{questions_completed} questions answered",
            )
        )

        return record
'''

new_completion = '''    def complete_practice_session(
        self,
        user_id: str,
        topic_name: str,
        questions_completed: int,
        completion_id: str | None = None,
    ) -> TopicLearningProgress:
        if questions_completed < 1:
            raise ValueError(
                "A completed practice session must contain "
                "at least one answered question."
            )

        key = self._key(user_id, topic_name)

        completion_key = None

        if completion_id is not None:
            completion_id = completion_id.strip()

            if not completion_id:
                raise ValueError(
                    "completion_id cannot be blank."
                )

            completion_key = (
                key[0],
                key[1],
                completion_id,
            )

            if completion_key in self._recorded_completions:
                return self._records[key]

        record = self.start_topic(
            user_id=user_id,
            topic_name=topic_name,
        )

        now = datetime.now()

        record.completed_practice_sessions += 1
        record.total_practice_questions += questions_completed
        record.last_activity_at = now

        record.events.append(
            TopicProgressEvent(
                event_type="practice_session_completed",
                recorded_at=now,
                detail=f"{questions_completed} questions answered",
            )
        )

        if completion_key is not None:
            self._recorded_completions.add(
                completion_key
            )

        return record
'''

assert source.count(old_init) == 1, (
    "Expected tracker initialization not found exactly once."
)

assert source.count(old_completion) == 1, (
    "Expected original completion method not found exactly once."
)

assert "_recorded_completions" not in source, (
    "Deduplication appears to be installed already."
)

updated = source.replace(
    old_init,
    new_init,
    1,
).replace(
    old_completion,
    new_completion,
    1,
)

shutil.copy2(path, backup)
path.write_text(updated, encoding="utf-8")

print("Backup created:", backup)
print("Completion deduplication installed.")
