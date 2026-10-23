"""Read-only, prerequisite-aware planning from actual shared cognitive evidence.

Readiness (.70 mastery, .50 confidence) follows the existing Learning Agent.
Seven-day revision is a prototype scheduling heuristic, not measured forgetting
or a validated spaced-repetition model. Viewing a plan changes no student data.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.cognitive.concept_identity import concept_id, clean_concept_name
from app.learning_agent.topic_bank import LearningTopicBank


def utc(value):
    # Legacy naive values were written using the application's local clock.
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class StudyStep:
    topic_name: str
    purpose: str
    difficulty: str
    reason: str
    blocked_by: tuple[str, ...] = ()


@dataclass(frozen=True)
class StudyPlan:
    goal_topic: str
    goal_steps: tuple[StudyStep, ...]
    revisions: tuple[StudyStep, ...]
    next_topics: tuple[StudyStep, ...]
    recommended: StudyStep | None
    custom_goal: bool


class LearningStudyPlanner:
    REVISION_INTERVAL = timedelta(days=7)

    def __init__(self, topic_bank=None):
        self.bank = topic_bank or LearningTopicBank()

    @staticmethod
    def has_conflict(student, engine, name):
        identity = concept_id(name)
        return any(owner == student.user_id and concept_id(topic) == identity and records
                   for (owner, topic), records in engine.active_conflicts.items())

    def ready(self, student, engine, name):
        state = student.find_concept(name)
        return bool(state is not None and state.attempts > 0 and state.mastery >= .70
                    and state.confidence >= .50 and not state.misconceptions
                    and not state.get_active_misconceptions() and not state.get_uncertain_misconceptions()
                    and not self.has_conflict(student, engine, name))

    def describe(self, student, engine, name, *, revision=False, blocked_by=()):
        name = clean_concept_name(name)
        state = student.find_concept(name)
        if self.has_conflict(student, engine, name):
            return StudyStep(name, "diagnostic", "medium",
                "Assessed evidence from different agents conflicts. Resolve it before progressing.")
        if state is None or state.attempts == 0:
            return StudyStep(name, "learn", "easy", "No assessed understanding is recorded yet.", blocked_by)
        if state.misconceptions or state.get_active_misconceptions():
            return StudyStep(name, "remediate", "easy",
                "An active misconception hypothesis needs focused explanation and reassessment.", blocked_by)
        if state.get_uncertain_misconceptions():
            return StudyStep(name, "verify", "medium",
                "A misconception hypothesis remains uncertain; collect targeted verification evidence.", blocked_by)
        if state.mastery < .40:
            return StudyStep(name, "remediate", "easy", "Recent assessed performance indicates a weak area.", blocked_by)
        if state.mastery < .70:
            return StudyStep(name, "practice", "medium", "Additional assessed practice can strengthen partial understanding.", blocked_by)
        if state.confidence < .50:
            return StudyStep(name, "verify", "hard", "The mastery estimate needs stronger independent verification.", blocked_by)
        return StudyStep(name, "revise" if revision else "extend", "hard",
            "At least seven days have passed since the latest assessed activity; verify retention."
            if revision else "Current assessed mastery and confidence support further application.", blocked_by)

    def create_plan(self, student, engine, goal_topic, *, now=None):
        goal_topic = clean_concept_name(goal_topic)
        goal = self.bank.get(goal_topic)
        if goal is not None:
            goal_topic = goal.name
        now = utc(now or datetime.now(timezone.utc))
        steps, visited, visiting = [], set(), set()

        def visit(name):
            key = concept_id(name)
            if key in visiting:
                raise ValueError("Circular prerequisite dependency in topic bank.")
            if key in visited:
                return
            visiting.add(key)
            topic = self.bank.get(name)
            if not self.ready(student, engine, name) and topic is not None:
                for prerequisite in topic.prerequisites:
                    if not self.ready(student, engine, prerequisite):
                        visit(prerequisite)
            blockers = tuple(p for p in (topic.prerequisites if topic else ())
                             if not self.ready(student, engine, p))
            if not self.ready(student, engine, name):
                steps.append(self.describe(student, engine, name, blocked_by=blockers))
            visiting.remove(key)
            visited.add(key)
        visit(goal_topic)

        revisions = []
        for state in student.concepts.values():
            if state.attempts == 0:
                continue
            evidence = engine.evidence_store.get_evidence_for_concept(student.user_id, state.concept_name)
            latest = max((utc(e.timestamp) for e in evidence), default=None)
            due = latest is not None and now - latest >= self.REVISION_INTERVAL
            if not self.ready(student, engine, state.concept_name) or due:
                revisions.append(self.describe(student, engine, state.concept_name, revision=due))
        priority = {"diagnostic": 0, "remediate": 1, "verify": 2, "practice": 3, "revise": 4}
        revisions.sort(key=lambda step: (priority.get(step.purpose, 5), concept_id(step.topic_name)))
        # A goal with a conflict can be unassessed in legacy data; retain it too.
        urgent = next((s for s in (*revisions, *steps) if s.purpose == "diagnostic"), None)
        urgent = urgent or next((s for s in revisions if s.purpose in ("remediate", "verify")), None)
        recommended = urgent or next((s for s in steps if not s.blocked_by), None)
        recommended = recommended or (revisions[0] if revisions else None)

        next_topics = []
        for topic in self.bank.all_topics():
            if concept_id(topic.name) in visited or self.ready(student, engine, topic.name):
                continue
            if all(self.ready(student, engine, p) for p in topic.prerequisites):
                next_topics.append(self.describe(student, engine, topic.name))
        if recommended is None and next_topics:
            recommended = next_topics[0]
        return StudyPlan(goal_topic, tuple(steps), tuple(revisions), tuple(next_topics[:3]), recommended, goal is None)

    @staticmethod
    def completed_sessions(student, engine):
        """Detailed history only from recorded, completed assessment outcomes."""
        found = {}
        for (owner, _), record in engine.assessment_records.items():
            if owner != student.user_id:
                continue
            outcome = record.get("stages", {}).get("outcome")
            summary = getattr(outcome, "summary", None)
            session = getattr(outcome, "session", None)
            if summary is not None and session is not None and session.is_complete:
                found[session.session_id] = (session, summary)
        return sorted(found.values(), key=lambda item: utc(item[0].completed_at or item[0].started_at), reverse=True)
