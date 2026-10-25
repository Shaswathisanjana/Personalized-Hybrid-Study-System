"""Tests for misconception detection, persistence, and automated rectification."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from cognitive_learning_agent.models.db_models import Base
from cognitive_learning_agent.memory.repository import CognitiveMemoryRepository
from cognitive_learning_agent.cognitive_engine.misconception_manager import MisconceptionManager
from cognitive_learning_agent.models.schemas import (
    LearnerProfileCreate,
    AssessmentFeedback,
    MisconceptionStatus,
)


@pytest.fixture
def misc_setup():
    test_engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    @contextmanager
    def test_session_factory():
        session = TestingSessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    repo = CognitiveMemoryRepository(test_session_factory)
    mgr = MisconceptionManager(repo)
    repo.upsert_learner(
        LearnerProfileCreate(
            user_id="learner_misc",
            name="Charlie",
            learning_goal="Learn Python Async",
            target_outcome="Build async API client",
        )
    )
    return repo, mgr


def test_misconception_detection(misc_setup):
    repo, mgr = misc_setup
    concept = "Python Event Loop & Coroutines"

    fb_fail = AssessmentFeedback(
        learner_id="learner_misc",
        concept_name=concept,
        completed=True,
        quiz_score=0.25,
        perceived_difficulty="too_hard",
        confusion_reported=True,
        notes="I thought async means code runs on all CPU cores simultaneously.",
    )

    detected = mgr.process_feedback(fb_fail)
    assert detected is not None
    assert detected.status == MisconceptionStatus.ACTIVE
    assert detected.concept_name == concept

    active_items = repo.get_active_misconceptions("learner_misc", concept)
    assert len(active_items) == 1
    assert "conflating" in active_items[0].description.lower() or "multithreading" in active_items[0].description.lower() or "async" in active_items[0].description.lower()


def test_misconception_rectification(misc_setup):
    repo, mgr = misc_setup
    concept = "Python Event Loop & Coroutines"

    # 1. Trigger misconception
    fb_fail = AssessmentFeedback(
        learner_id="learner_misc",
        concept_name=concept,
        completed=True,
        quiz_score=0.30,
        confusion_reported=True,
        notes="Confusion about event loop thread model",
    )
    mgr.process_feedback(fb_fail)
    assert len(repo.get_active_misconceptions("learner_misc", concept)) == 1

    # 2. Learner studies remedial resource and passes assessment with 85%
    fb_pass = AssessmentFeedback(
        learner_id="learner_misc",
        concept_name=concept,
        completed=True,
        quiz_score=0.85,
        confusion_reported=False,
        notes="Now understood single-threaded cooperative multitasking!",
    )
    mgr.process_feedback(fb_pass)

    # Invariant: Active misconception should now be resolved
    assert len(repo.get_active_misconceptions("learner_misc", concept)) == 0
    all_misc = repo.get_all_misconceptions("learner_misc")
    assert len(all_misc) == 1
    assert all_misc[0].status == MisconceptionStatus.RECTIFIED
    assert "Resolved" in (all_misc[0].remediation_notes or "")
