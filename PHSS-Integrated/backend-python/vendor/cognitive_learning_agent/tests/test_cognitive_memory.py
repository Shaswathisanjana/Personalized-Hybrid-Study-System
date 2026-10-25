"""Tests for cognitive memory persistence, models, and evidence isolation."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from cognitive_learning_agent.models.db_models import Base
from cognitive_learning_agent.memory.repository import CognitiveMemoryRepository
from cognitive_learning_agent.models.schemas import (
    LearnerProfileCreate,
    DifficultyLevel,
    LearningFormat,
    ConceptMasteryItem,
    ConceptStatus,
    EvidenceItem,
    EvidenceType,
)


@pytest.fixture
def repo():
    # In-memory SQLite database for test isolation
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

    return CognitiveMemoryRepository(test_session_factory)


def test_learner_profile_persistence(repo):
    profile_data = LearnerProfileCreate(
        user_id="test_user_42",
        name="Jordan",
        learning_goal="Understand Transformer Attention",
        current_level=DifficultyLevel.BEGINNER,
        preferred_format=LearningFormat.VIDEO,
        target_outcome="Implement self-attention in PyTorch",
        preferred_language="Python",
    )

    saved = repo.upsert_learner(profile_data)
    assert saved.user_id == "test_user_42"
    assert saved.name == "Jordan"

    retrieved = repo.get_learner("test_user_42")
    assert retrieved is not None
    assert retrieved.learning_goal == "Understand Transformer Attention"
    assert retrieved.current_level == DifficultyLevel.BEGINNER


def test_concept_mastery_persistence(repo):
    # Setup learner
    repo.upsert_learner(
        LearnerProfileCreate(
            user_id="user_cm",
            name="Alice",
            learning_goal="Learn FastAPI",
            target_outcome="Build a microservice",
        )
    )

    c_item = ConceptMasteryItem(
        concept_name="Pydantic Models",
        mastery_score=0.78,
        confidence_score=0.65,
        status=ConceptStatus.PROFICIENT,
        evidence_count=2,
    )
    repo.upsert_concept_mastery("user_cm", c_item)

    masteries = repo.get_concept_masteries("user_cm")
    assert "Pydantic Models" in masteries
    assert masteries["Pydantic Models"].mastery_score == 0.78
    assert masteries["Pydantic Models"].status == ConceptStatus.PROFICIENT


def test_evidence_store_persistence(repo):
    repo.upsert_learner(
        LearnerProfileCreate(
            user_id="user_ev",
            name="Bob",
            learning_goal="Learn Docker",
            target_outcome="Containerize app",
        )
    )

    ev = EvidenceItem(
        learner_id="user_ev",
        concept_name="Dockerfiles",
        evidence_type=EvidenceType.QUIZ,
        score=0.90,
        observation="Passed 9/10 quiz questions on multi-stage builds",
        user_feedback_rating=5,
    )
    saved_ev = repo.add_evidence(ev)
    assert saved_ev.id is not None

    fetched = repo.get_evidence_for_concept("user_ev", "Dockerfiles")
    assert len(fetched) == 1
    assert fetched[0].score == 0.90
    assert fetched[0].evidence_type == EvidenceType.QUIZ
