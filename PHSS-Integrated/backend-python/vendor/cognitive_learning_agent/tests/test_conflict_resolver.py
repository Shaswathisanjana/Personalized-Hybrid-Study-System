"""Tests for cognitive conflict detection and resolution."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from cognitive_learning_agent.models.db_models import Base
from cognitive_learning_agent.memory.repository import CognitiveMemoryRepository
from cognitive_learning_agent.cognitive_engine.conflict_detector import ConflictDetectorResolver
from cognitive_learning_agent.models.schemas import (
    LearnerProfileCreate,
    DifficultyLevel,
    ConceptMasteryItem,
    ConceptStatus,
    AssessmentFeedback,
    ConflictSeverity,
)


@pytest.fixture
def conflict_setup():
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
    detector = ConflictDetectorResolver(repo)

    # Learner claims "Advanced" level
    repo.upsert_learner(
        LearnerProfileCreate(
            user_id="advanced_learner",
            name="Diana",
            learning_goal="Distributed Systems in Python",
            current_level=DifficultyLevel.ADVANCED,
            target_outcome="Build a Raft consensus node",
        )
    )

    # Initial concept mastery with high confidence
    repo.upsert_concept_mastery(
        "advanced_learner",
        ConceptMasteryItem(
            concept_name="Async Concurrency",
            mastery_score=0.80,
            confidence_score=0.85,
            status=ConceptStatus.PROFICIENT,
        ),
    )

    return repo, detector


def test_claimed_mastery_vs_measured_failure_conflict(conflict_setup):
    repo, detector = conflict_setup
    concept = "Async Concurrency"

    # Assessment contradicts claimed advanced competence
    fb = AssessmentFeedback(
        learner_id="advanced_learner",
        concept_name=concept,
        completed=True,
        quiz_score=0.20,
        perceived_difficulty="too_hard",
    )

    conflicts = detector.detect_and_resolve(fb)
    assert len(conflicts) >= 1
    assert any(c.severity in (ConflictSeverity.HIGH, ConflictSeverity.MEDIUM) for c in conflicts)

    # Invariant: Confidence must be penalized
    updated_mastery = repo.get_concept_masteries("advanced_learner")[concept]
    assert updated_mastery.confidence_score < 0.85
    assert "penalized" in (updated_mastery.notes or "").lower()


def test_prerequisite_inversion_conflict(conflict_setup):
    repo, detector = conflict_setup
    # Concept B requires Concept A
    repo.add_prerequisite("advanced_learner", "Advanced Distributed Locks", "Basic Socket IO")

    # Prerequisite has 0 mastery
    repo.upsert_concept_mastery(
        "advanced_learner",
        ConceptMasteryItem(
            concept_name="Basic Socket IO",
            mastery_score=0.10,
            status=ConceptStatus.NOT_STARTED,
        ),
    )

    fb = AssessmentFeedback(
        learner_id="advanced_learner",
        concept_name="Advanced Distributed Locks",
        completed=True,
        quiz_score=0.30,
    )

    conflicts = detector.detect_and_resolve(fb)
    prereq_conflicts = [c for c in conflicts if "prerequisite" in c.description.lower()]
    assert len(prereq_conflicts) >= 1
    assert prereq_conflicts[0].severity == ConflictSeverity.HIGH
