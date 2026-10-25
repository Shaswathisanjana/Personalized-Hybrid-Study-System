"""Tests for adaptive re-planning based on learner feedback and cognitive state."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from cognitive_learning_agent.models.db_models import Base
from cognitive_learning_agent.memory.repository import CognitiveMemoryRepository
from cognitive_learning_agent.cognitive_engine.replanner import AgentReplanner
from cognitive_learning_agent.discovery.searcher import ResourceSearcher
from cognitive_learning_agent.discovery.extractor import PageExtractor
from cognitive_learning_agent.discovery.validator import LinkValidator
from cognitive_learning_agent.discovery.ranker import ResourceRanker
from cognitive_learning_agent.models.schemas import (
    LearnerProfileCreate,
    DifficultyLevel,
    LearningFormat,
    LearningPath,
    LearningResource,
    AssessmentFeedback,
    ConceptMasteryItem,
    ConceptStatus,
)


@pytest.fixture
def replanner_setup():
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
    searcher = ResourceSearcher()
    searcher.search_for_concept = lambda concept_name, **kwargs: [
        {
            "url": f"https://docs.python.org/3/library/{concept_name.lower().replace(' ', '-')}.html",
            "title": f"Tutorial on {concept_name}",
            "snippet": f"Foundational guide to {concept_name}",
            "domain": "docs.python.org",
            "concept": concept_name,
        }
    ]
    extractor = PageExtractor()
    extractor.extract_metadata = lambda url, initial_title="", initial_snippet="": {
        "title": initial_title or "Tutorial",
        "description": initial_snippet or "Guide",
        "domain": "docs.python.org",
        "format": LearningFormat.DOCUMENTATION,
        "word_count": 800,
        "estimated_minutes": 10,
    }
    validator = LinkValidator()
    validator.check_link = lambda url: (True, 200, url)  # Deterministic test bypass
    ranker = ResourceRanker()

    replanner = AgentReplanner(repo, searcher, extractor, validator, ranker)

    # Initialize learner profile
    user_id = "replan_user"
    repo.upsert_learner(
        LearnerProfileCreate(
            user_id=user_id,
            name="Evan",
            learning_goal="Master Asyncio",
            current_level=DifficultyLevel.BEGINNER,
            preferred_format=LearningFormat.DOCUMENTATION,
            target_outcome="Build an async crawler",
        )
    )

    # Add concepts and prerequisite: Event Loop -> Task Management
    repo.add_prerequisite(user_id, "Task Management", "Event Loop Fundamentals")
    repo.upsert_concept_mastery(
        user_id,
        ConceptMasteryItem(
            concept_name="Event Loop Fundamentals",
            mastery_score=0.20,
            status=ConceptStatus.IN_PROGRESS,
        ),
    )
    repo.upsert_concept_mastery(
        user_id,
        ConceptMasteryItem(
            concept_name="Task Management",
            mastery_score=0.10,
            status=ConceptStatus.NOT_STARTED,
        ),
    )

    initial_path = LearningPath(
        learner_id=user_id,
        goal="Master Asyncio",
        target_outcome="Build an async crawler",
        ordered_concepts=["Event Loop Fundamentals", "Task Management"],
        resources=[
            LearningResource(
                url="https://docs.python.org/3/library/asyncio-task.html",
                title="Coroutines and Tasks",
                snippet="Documentation on asyncio tasks",
                domain="docs.python.org",
                format=LearningFormat.DOCUMENTATION,
                difficulty=DifficultyLevel.INTERMEDIATE,
                target_concept="Task Management",
                relevance_score=0.85,
            )
        ],
    )

    return repo, replanner, user_id, initial_path


def test_replanning_when_learner_struggles(replanner_setup):
    repo, replanner, user_id, initial_path = replanner_setup

    # Learner attempts Task Management and fails (quiz 25%, too hard)
    feedback = AssessmentFeedback(
        learner_id=user_id,
        concept_name="Task Management",
        resource_url="https://docs.python.org/3/library/asyncio-task.html",
        completed=True,
        quiz_score=0.25,
        perceived_difficulty="too_hard",
        confusion_reported=True,
        notes="Cannot understand how tasks are scheduled on the loop.",
    )

    replan_result = replanner.replan(
        user_id=user_id,
        current_path=initial_path,
        latest_feedback=feedback,
    )

    # Invariants for Adaptive Replanning:
    # 1. Replan must be triggered
    assert replan_result.replan_triggered is True
    assert len(replan_result.reasons) > 0

    # 2. Replan must address prerequisite remediation or stepped-down difficulty
    action_texts = " ".join(replan_result.actions_taken).lower()
    assert "prerequisite" in action_texts or "alternative" in action_texts or "difficulty" in action_texts

    # 3. Updated learning path must contain remedial or stepped-down resources
    updated_resources = replan_result.updated_learning_path.resources
    assert len(updated_resources) >= 1
    # Check that prerequisite 'Event Loop Fundamentals' is prioritized or injected
    concepts_in_updated = [r.target_concept for r in updated_resources]
    assert "Event Loop Fundamentals" in concepts_in_updated or any(
        "remediation" in (r.snippet or "").lower() for r in updated_resources
    )
