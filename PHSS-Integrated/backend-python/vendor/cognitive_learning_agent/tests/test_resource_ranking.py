"""Tests for resource relevance ranking, format weighting, and difficulty matching."""

import pytest
from cognitive_learning_agent.discovery.ranker import ResourceRanker
from cognitive_learning_agent.models.schemas import DifficultyLevel, LearningFormat


def test_ranking_relevance_and_sorting():
    ranker = ResourceRanker()

    candidates = [
        {
            "url": "https://random-blog.com/cooking-recipes",
            "title": "Best Italian Pasta Recipes",
            "description": "How to make homemade fettuccine and marinara sauce from scratch.",
            "format": LearningFormat.DOCUMENTATION,
            "domain": "random-blog.com",
        },
        {
            "url": "https://realpython.com/async-io-python/",
            "title": "Async IO in Python: A Complete Walkthrough",
            "description": "Comprehensive tutorial on asynchronous coroutines, event loops, and tasks in Python.",
            "format": LearningFormat.DOCUMENTATION,
            "domain": "realpython.com",
        },
    ]

    ranked = ranker.rank_resources(
        candidate_items=candidates,
        target_concept="Python Event Loop & Coroutines",
        learning_goal="Master Python asyncio and concurrency",
        learner_level=DifficultyLevel.BEGINNER,
    )

    assert len(ranked) == 2
    # The relevant tutorial must be ranked first with a significantly higher score
    assert ranked[0].domain == "realpython.com"
    assert ranked[0].relevance_score > ranked[1].relevance_score


def test_format_preference_boost():
    ranker = ResourceRanker()

    candidates = [
        {
            "url": "https://docs.python.org/3/library/asyncio.html",
            "title": "asyncio Documentation",
            "description": "Official Python asyncio reference and guide.",
            "format": LearningFormat.DOCUMENTATION,
            "domain": "docs.python.org",
        },
        {
            "url": "https://youtube.com/watch?v=12345",
            "title": "Python Asyncio Visualized and Explained",
            "description": "Video walkthrough showing event loop execution step by step.",
            "format": LearningFormat.VIDEO,
            "domain": "youtube.com",
        },
    ]

    # When video format is preferred:
    ranked_video_pref = ranker.rank_resources(
        candidate_items=candidates,
        target_concept="asyncio",
        learning_goal="Learn asyncio",
        preferred_format=LearningFormat.VIDEO,
    )

    video_res = next(r for r in ranked_video_pref if r.format == LearningFormat.VIDEO)
    docs_res = next(r for r in ranked_video_pref if r.format == LearningFormat.DOCUMENTATION)

    assert video_res.format == LearningFormat.VIDEO
    assert video_res.relevance_score >= docs_res.relevance_score
