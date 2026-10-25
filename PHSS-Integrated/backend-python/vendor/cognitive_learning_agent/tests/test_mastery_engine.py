"""Tests for evidence-based Bayesian/EWMA mastery calculation and confidence scaling."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from cognitive_learning_agent.models.db_models import Base
from cognitive_learning_agent.memory.repository import CognitiveMemoryRepository
from cognitive_learning_agent.cognitive_engine.mastery_engine import MasteryEngine
from cognitive_learning_agent.models.schemas import (
    LearnerProfileCreate,
    EvidenceItem,
    EvidenceType,
    ConceptStatus,
)


@pytest.fixture
def mastery_setup():
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
    engine = MasteryEngine(repo)
    repo.upsert_learner(
        LearnerProfileCreate(
            user_id="user_mastery",
            name="Test Learner",
            learning_goal="Master Concurrency",
            target_outcome="Build an async queue",
        )
    )
    return repo, engine


def test_no_evidence_not_started(mastery_setup):
    repo, engine = mastery_setup
    res = engine.update_concept_mastery("user_mastery", "Async Event Loop")
    assert res.status == ConceptStatus.NOT_STARTED
    assert res.mastery_score == 0.0
    assert res.evidence_count == 0


def test_invariant_never_premature_mastery(mastery_setup):
    repo, engine = mastery_setup
    concept = "Async Event Loop"

    # User self-reports high understanding, but only 1 evidence item without verified quiz
    repo.add_evidence(
        EvidenceItem(
            learner_id="user_mastery",
            concept_name=concept,
            evidence_type=EvidenceType.SELF_RATING,
            score=0.95,
            observation="Self rating 5/5",
        )
    )

    item1 = engine.update_concept_mastery("user_mastery", concept)
    # INVARIANT: Must NOT be MASTERED because evidence_count < 3 and no verified quiz
    assert item1.status != ConceptStatus.MASTERED


def test_full_mastery_with_sufficient_verified_evidence(mastery_setup):
    repo, engine = mastery_setup
    concept = "Async Event Loop"

    # Provide 3 strong evidence items with quiz validation
    repo.add_evidence(
        EvidenceItem(
            learner_id="user_mastery",
            concept_name=concept,
            evidence_type=EvidenceType.COMPLETION,
            score=0.85,
            observation="Completed tutorial walkthrough",
        )
    )
    repo.add_evidence(
        EvidenceItem(
            learner_id="user_mastery",
            concept_name=concept,
            evidence_type=EvidenceType.PRACTICE,
            score=0.90,
            observation="Solved 5 practice tasks",
        )
    )
    repo.add_evidence(
        EvidenceItem(
            learner_id="user_mastery",
            concept_name=concept,
            evidence_type=EvidenceType.QUIZ,
            score=0.95,
            observation="Scored 95% on comprehensive quiz",
        )
    )

    item = engine.update_concept_mastery("user_mastery", concept)
    assert item.status == ConceptStatus.MASTERED
    assert item.mastery_score >= 0.88
    assert item.confidence_score >= 0.70
    assert item.evidence_count == 3
