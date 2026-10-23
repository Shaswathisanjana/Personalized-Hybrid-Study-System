from app.cognitive.concept_identity import concept_id
from dataclasses import dataclass, field
from datetime import datetime

from app.cognitive.models import StudentCognitiveModel


@dataclass(frozen=True)
class TopicProgressEvent:
    event_type: str
    recorded_at: datetime
    detail: str = ""


@dataclass
class TopicLearningProgress:
    topic_name: str
    started_at: datetime
    last_activity_at: datetime
    completed_practice_sessions: int = 0
    total_practice_questions: int = 0
    events: list[TopicProgressEvent] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.completed_practice_sessions > 0:
            return "practice_completed"

        return "started"


@dataclass(frozen=True)
class TopicProgressSnapshot:
    topic_name: str
    status: str
    started_at: datetime
    last_activity_at: datetime
    completed_practice_sessions: int
    total_practice_questions: int
    mastery: float | None
    confidence: float | None
    cognitive_attempts: int


class LearningProgressTracker:
    """
    Records student learning activity separately from CACM.

    This tracker never calculates or modifies mastery.
    """

    def __init__(self):
        self._records: dict[
            tuple[str, str],
            TopicLearningProgress,
        ] = {}

        # Prevent duplicate completion events for the same
        # student, topic and practice session.
        self._recorded_completions: set[
            tuple[str, str, str]
        ] = set()

    @staticmethod
    def _key(user_id: str, topic_name: str) -> tuple[str, str]:
        user_id = user_id.strip()
        topic_name = topic_name.strip()

        if not user_id or not topic_name:
            raise ValueError(
                "user_id and topic_name must not be empty."
            )

        return user_id, concept_id(topic_name)

    def start_topic(
        self,
        user_id: str,
        topic_name: str,
    ) -> TopicLearningProgress:
        key = self._key(user_id, topic_name)

        if key in self._records:
            return self._records[key]

        now = datetime.now()

        record = TopicLearningProgress(
            topic_name=topic_name.strip(),
            started_at=now,
            last_activity_at=now,
            events=[
                TopicProgressEvent(
                    event_type="topic_started",
                    recorded_at=now,
                )
            ],
        )

        self._records[key] = record

        return record

    def complete_practice_session(
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

    def get_progress(
        self,
        user_id: str,
        topic_name: str,
    ) -> TopicLearningProgress | None:
        return self._records.get(
            self._key(user_id, topic_name)
        )

    def list_progress(
        self,
        user_id: str,
    ) -> list[TopicLearningProgress]:
        user_id = user_id.strip()

        if not user_id:
            raise ValueError("user_id must not be empty.")

        records = [
            record
            for (owner_id, _), record in self._records.items()
            if owner_id == user_id
        ]

        return sorted(
            records,
            key=lambda record: record.last_activity_at,
            reverse=True,
        )

    def snapshot(
        self,
        student: StudentCognitiveModel,
        topic_name: str,
    ) -> TopicProgressSnapshot | None:
        record = self.get_progress(
            student.user_id,
            topic_name,
        )

        if record is None:
            return None

        # Read existing cognitive state without creating
        # a new default ConceptState for an unseen topic.
        state = student.find_concept(record.topic_name)

        return TopicProgressSnapshot(
            topic_name=record.topic_name,
            status=record.status,
            started_at=record.started_at,
            last_activity_at=record.last_activity_at,
            completed_practice_sessions=(
                record.completed_practice_sessions
            ),
            total_practice_questions=(
                record.total_practice_questions
            ),
            mastery=state.mastery if state is not None else None,
            confidence=(
                state.confidence if state is not None else None
            ),
            cognitive_attempts=(
                state.attempts if state is not None else 0
            ),
        )
