"""Unit tests for Quiz Generation, Evaluation, Weak Area Diagnosis, and Targeted Remediation."""

import pytest
from cognitive_learning_agent.core.agent import LearningAgent
from cognitive_learning_agent.models.schemas import (
    LearnerProfileCreate,
    DifficultyLevel,
    LearningFormat,
    LearningResource,
    QuizSubmission,
    QuizEvaluationResult,
    QuestionType,
)


@pytest.fixture
def mock_agent():
    agent = LearningAgent()
    # Offline LLM
    agent.llm._groq_client = None
    agent.llm._gemini_client = None
    # Mock searcher, validator, and extractor to prevent live network calls in unit tests
    agent.searcher.search_for_concept = lambda concept_name, **kwargs: [
        {
            "url": f"https://docs.python.org/3/library/{concept_name.lower().replace(' ', '-').replace('&', 'and')}.html",
            "title": f"Official Guide: {concept_name}",
            "snippet": f"In-depth documentation covering {concept_name}.",
            "domain": "docs.python.org",
            "concept": concept_name,
        },
        {
            "url": f"https://realpython.com/{concept_name.lower().replace(' ', '-').replace('&', 'and')}/",
            "title": f"Real Python: Mastering {concept_name}",
            "snippet": f"Step-by-step tutorial addressing common pitfalls in {concept_name}.",
            "domain": "realpython.com",
            "concept": concept_name,
        },
    ]
    agent.validator.validate_and_deduplicate = lambda raw: raw
    agent.extractor.extract_metadata = lambda url, initial_title="", initial_snippet="": {
        "title": initial_title or "Documentation Guide",
        "description": initial_snippet or "Detailed documentation",
        "domain": "docs.python.org",
        "word_count": 850,
        "estimated_reading_time_minutes": 10,
        "format": LearningFormat.DOCUMENTATION,
        "code_snippet_count": 4,
    }
    agent.ranker.rank_resources = lambda candidate_items, target_concept, **kwargs: [
        LearningResource(
            url=c["url"],
            title=c.get("title", f"Guide to {target_concept}"),
            snippet=c.get("snippet", ""),
            domain=c.get("domain", "example.com"),
            format=LearningFormat.DOCUMENTATION,
            difficulty=DifficultyLevel.BEGINNER,
            target_concept=target_concept,
            relevance_score=0.92,
            is_valid=True,
            estimated_minutes=12,
        )
        for c in candidate_items
    ]
    agent.replanner.searcher = agent.searcher
    agent.replanner.validator = agent.validator
    agent.replanner.extractor = agent.extractor
    agent.replanner.ranker = agent.ranker
    return agent


def test_quiz_generation(mock_agent):
    agent = mock_agent
    user_id = "test_quiz_gen_user"

    agent.start_learning_journey(
        LearnerProfileCreate(
            user_id=user_id,
            name="Quiz Tester",
            learning_goal="Understand Python asyncio event loop and coroutines",
            current_level=DifficultyLevel.BEGINNER,
            preferred_format=LearningFormat.DOCUMENTATION,
            target_outcome="Build an async scraper",
        )
    )

    quiz = agent.generate_quiz_for_resource(
        user_id=user_id,
        concept_name="Python Event Loop & Coroutines",
        resource_url="https://docs.python.org/3/library/asyncio.html",
    )

    assert quiz is not None
    assert quiz.concept_name == "Python Event Loop & Coroutines"
    # Must have exactly 10 questions
    assert len(quiz.questions) == 10

    mcqs = [q for q in quiz.questions if q.question_type == QuestionType.MCQ]
    descriptives = [q for q in quiz.questions if q.question_type == QuestionType.DESCRIPTIVE]

    assert len(mcqs) >= 4, "Must contain multiple choice questions"
    assert len(descriptives) >= 2, "Must contain descriptive conceptual questions"

    for q in mcqs:
        assert q.question_text
        assert len(q.options) >= 2
        assert 0 <= q.correct_option_index < len(q.options)
        assert q.concept_aspect

    for q in descriptives:
        assert q.question_text
        assert q.ideal_answer
        assert len(q.rubric_keywords) > 0
        assert q.concept_aspect


def test_quiz_evaluation_identifies_weak_areas_and_targeted_resources(mock_agent):
    agent = mock_agent
    user_id = "test_quiz_eval_user"

    agent.start_learning_journey(
        LearnerProfileCreate(
            user_id=user_id,
            name="Quiz Learner",
            learning_goal="Master Python asyncio programming",
            current_level=DifficultyLevel.BEGINNER,
            preferred_format=LearningFormat.DOCUMENTATION,
            target_outcome="Understand concurrency",
        )
    )

    quiz = agent.generate_quiz_for_resource(
        user_id=user_id,
        concept_name="Python Event Loop & Coroutines",
        resource_url="https://docs.python.org/3/library/asyncio.html",
    )

    # Intentionally submit incorrect answers for first 2 MCQs and inadequate answer for first descriptive
    selected_answers = {}
    descriptive_answers = {}
    mcqs_failed = 0
    descs_failed = 0

    for q in quiz.questions:
        if q.question_type == QuestionType.MCQ:
            if mcqs_failed < 3:
                # choose wrong distractor
                selected_answers[q.question_id] = (q.correct_option_index + 1) % len(q.options)
                mcqs_failed += 1
            else:
                selected_answers[q.question_id] = q.correct_option_index
        else:
            if descs_failed < 1:
                # inadequate / missing keywords
                descriptive_answers[q.question_id] = "I do not know"
                descs_failed += 1
            else:
                # complete answer with rubric keywords
                descriptive_answers[q.question_id] = q.ideal_answer or " ".join(q.rubric_keywords)

    submission = QuizSubmission(
        learner_id=user_id,
        concept_name="Python Event Loop & Coroutines",
        resource_url="https://docs.python.org/3/library/asyncio.html",
        selected_answers=selected_answers,
        descriptive_answers=descriptive_answers,
    )

    result: QuizEvaluationResult = agent.evaluate_quiz_and_remedy(submission)

    assert result.concept_name == "Python Event Loop & Coroutines"
    assert result.total_questions == 10
    assert result.score < 1.0
    assert not result.passed

    # Weak areas and misconceptions should be identified
    assert len(result.weak_areas) >= 1
    assert len(result.detected_misconceptions) >= 1

    # Targeted remedial resources should be found covering the weak areas
    assert len(result.targeted_resources) > 0
    for res in result.targeted_resources:
        assert res.url.startswith("http")
        assert res.title

    # Check cognitive memory state
    snapshot = agent.get_cognitive_state(user_id)
    assert snapshot is not None
    assert len(snapshot.active_misconceptions) >= 1
    assert len(snapshot.recent_evidence) >= 1


def test_quiz_perfect_score(mock_agent):
    agent = mock_agent
    user_id = "test_quiz_perfect_user"

    agent.start_learning_journey(
        LearnerProfileCreate(
            user_id=user_id,
            name="Perfect Learner",
            learning_goal="Master REST APIs with FastAPI",
            current_level=DifficultyLevel.INTERMEDIATE,
            preferred_format=LearningFormat.DOCUMENTATION,
            target_outcome="Build production APIs",
        )
    )

    quiz = agent.generate_quiz_for_resource(
        user_id=user_id,
        concept_name="HTTP Protocol & RESTful Architecture Principles",
        resource_url="https://restfulapi.net/",
    )

    # Submit all correct answers (both MCQs and descriptive)
    selected = {}
    descriptive = {}
    for q in quiz.questions:
        if q.question_type == QuestionType.MCQ:
            selected[q.question_id] = q.correct_option_index
        else:
            descriptive[q.question_id] = q.ideal_answer or " ".join(q.rubric_keywords)

    submission = QuizSubmission(
        learner_id=user_id,
        concept_name="HTTP Protocol & RESTful Architecture Principles",
        resource_url="https://restfulapi.net/",
        selected_answers=selected,
        descriptive_answers=descriptive,
    )

    result = agent.evaluate_quiz_and_remedy(submission)

    assert result.score >= 0.8
    assert result.passed
    assert len(result.weak_areas) == 0
    assert len(result.detected_misconceptions) == 0

    snapshot = agent.get_cognitive_state(user_id)
    assert snapshot is not None
    mastery_item = snapshot.concepts.get("HTTP Protocol & RESTful Architecture Principles")
    assert mastery_item is not None
    assert mastery_item.mastery_score > 0.3
