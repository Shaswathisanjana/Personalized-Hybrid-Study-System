"""Comprehensive Unit and Integration Tests for the Adaptive Quiz System with Cognitive Memory.

Validates:
1. First-time diagnostic quiz generation (Attempt #1).
2. Persistence of quiz history (attempts, questions, selected answers, scores, weak areas, misconceptions).
3. Cognitive memory update without premature mastery on single attempts.
4. Adaptive retake quiz generation (Attempt #2+) prioritizing missed concepts and misconceptions.
5. Predict Output coding questions with code snippets and option validation.
6. Revision retention questions from previously mastered concepts.
7. Cognitive remediation efficacy tracking (evaluating if recommended resources helped).
8. Pedagogical Next Learning Action decisions (PROCEED, REVISE, REVISIT_PREREQUISITE).
9. Memory persistence across sessions.
"""

import pytest
from cognitive_learning_agent.core.agent import LearningAgent
from cognitive_learning_agent.models.schemas import (
    LearnerProfileCreate,
    DifficultyLevel,
    LearningFormat,
    LearningResource,
    QuizSubmission,
    QuestionType,
    NextLearningAction,
    ConceptStatus,
)


def mock_agent_dependencies(agent):
    """Mocks network calls for searcher, extractor, validator, and ranker to ensure fast, deterministic tests."""
    agent.llm._groq_client = None
    agent.llm._gemini_client = None

    agent.searcher.search_for_concept = lambda concept_name, **kwargs: [
        {
            "url": f"https://docs.python.org/3/library/{concept_name.lower().replace(' ', '-').replace('&', 'and')}.html",
            "title": f"Official Guide: {concept_name}",
            "snippet": f"Authoritative documentation covering {concept_name}.",
            "domain": "docs.python.org",
            "concept": concept_name,
        },
        {
            "url": f"https://realpython.com/{concept_name.lower().replace(' ', '-').replace('&', 'and')}/",
            "title": f"Real Python Tutorial: {concept_name}",
            "snippet": f"Practical guide addressing common misconceptions in {concept_name}.",
            "domain": "realpython.com",
            "concept": concept_name,
        },
    ]
    agent.validator.validate_and_deduplicate = lambda raw: raw
    agent.extractor.extract_metadata = lambda url, initial_title="", initial_snippet="": {
        "title": initial_title or "Documentation Guide",
        "description": initial_snippet or "Detailed documentation",
        "domain": "docs.python.org",
        "word_count": 900,
        "estimated_reading_time_minutes": 10,
        "format": LearningFormat.DOCUMENTATION,
        "code_snippet_count": 5,
    }
    agent.ranker.rank_resources = lambda candidate_items, target_concept, **kwargs: [
        LearningResource(
            url=c["url"],
            title=c.get("title", f"Guide to {target_concept}"),
            snippet=c.get("snippet", ""),
            domain=c.get("domain", "docs.python.org"),
            format=LearningFormat.DOCUMENTATION,
            difficulty=DifficultyLevel.BEGINNER,
            target_concept=target_concept,
            relevance_score=0.92,
            is_valid=True,
            estimated_minutes=10,
        )
        for c in candidate_items
    ]
    agent.replanner.searcher = agent.searcher
    agent.replanner.validator = agent.validator
    agent.replanner.extractor = agent.extractor
    agent.replanner.ranker = agent.ranker
    return agent


@pytest.fixture
def mock_agent(tmp_path):
    # Use isolated test database
    db_path = str(tmp_path / "test_cognitive_memory.db")
    agent = LearningAgent(db_url=f"sqlite:///{db_path}")
    return mock_agent_dependencies(agent)


def test_first_time_diagnostic_quiz(mock_agent):
    """Attempt 1 must generate an initial diagnostic assessment."""
    agent = mock_agent
    user_id = "learner_001"

    agent.start_learning_journey(
        LearnerProfileCreate(
            user_id=user_id,
            name="Alice",
            learning_goal="Master Binary Trees and Traversal",
            current_level=DifficultyLevel.BEGINNER,
            preferred_format=LearningFormat.DOCUMENTATION,
            target_outcome="Implement balanced BSTs",
        )
    )

    quiz = agent.generate_quiz_for_resource(
        user_id=user_id,
        concept_name="Binary Trees & Traversal",
        resource_url="https://docs.python.org/3/library/trees.html",
    )

    assert quiz is not None
    assert quiz.concept_name == "Binary Trees & Traversal"
    assert quiz.attempt_number == 1
    assert quiz.quiz_type == "initial"
    assert len(quiz.questions) == 10

    # Must contain both objective questions (MCQ / Predict Output) and conceptual descriptive questions
    objective_questions = [q for q in quiz.questions if q.question_type in (QuestionType.MCQ, QuestionType.PREDICT_OUTPUT)]
    descriptives = [q for q in quiz.questions if q.question_type == QuestionType.DESCRIPTIVE]
    assert len(objective_questions) == 6
    assert len(descriptives) == 4


def test_quiz_attempt_persistence_and_no_premature_mastery(mock_agent):
    """Quiz submission must persist attempt history and avoid granting instant mastery on 1 attempt."""
    agent = mock_agent
    user_id = "learner_002"

    agent.start_learning_journey(
        LearnerProfileCreate(
            user_id=user_id,
            name="Bob",
            learning_goal="Understand Python Asyncio",
            current_level=DifficultyLevel.BEGINNER,
            preferred_format=LearningFormat.DOCUMENTATION,
            target_outcome="Build an async API",
        )
    )

    # First attempt: Bob gets some questions wrong
    eval_result = agent.evaluate_quiz_and_remedy(
        user_id=user_id,
        submission=QuizSubmission(
            learner_id=user_id,
            concept_name="Python Event Loop & Coroutines",
            resource_url="https://docs.python.org/3/library/asyncio.html",
            attempt_number=1,
            selected_answers={1: 0, 2: 0, 3: 1, 4: 1, 5: 2, 6: 2},
            descriptive_answers={
                7: "The event loop runs tasks concurrently on a single thread.",
                8: "asyncio.gather runs things.",
            },
        ),
    )

    assert eval_result.attempt_number == 1
    assert eval_result.quiz_type == "initial"
    assert len(eval_result.weak_areas) > 0
    assert len(eval_result.misconceptions) > 0
    assert len(eval_result.targeted_resources) > 0

    # History in repository
    history = agent.repo.get_quiz_attempts(user_id=user_id, concept_name="Python Event Loop & Coroutines")
    assert len(history) == 1
    assert history[0].attempt_number == 1
    assert history[0].score == eval_result.score
    assert len(history[0].weak_areas) == len(eval_result.weak_areas)

    # Mastery invariant: Even with a high score, single attempt should not declare mastery
    masteries = agent.repo.get_concept_masteries(user_id)
    concept_prof = masteries.get("Python Event Loop & Coroutines")
    assert concept_prof is not None
    assert concept_prof.status != ConceptStatus.MASTERED, "Single attempt must never mark concept as MASTERED"
    assert concept_prof.mastery_score < 0.85


def test_adaptive_retake_quiz_with_predict_output_and_revision(mock_agent):
    """Attempt 2 must generate an adaptive quiz targeting weak areas and include Predict Output code questions."""
    agent = mock_agent
    user_id = "learner_003"

    agent.start_learning_journey(
        LearnerProfileCreate(
            user_id=user_id,
            name="Carol",
            learning_goal="Learn Tree Traversals",
            current_level=DifficultyLevel.BEGINNER,
            preferred_format=LearningFormat.DOCUMENTATION,
            target_outcome="Implement Inorder/Preorder/Postorder traversals",
        )
    )

    concept_name = "Binary Tree Traversals"

    # Seed Attempt 1 with poor performance to diagnose weak areas
    agent.evaluate_quiz_and_remedy(
        user_id=user_id,
        submission=QuizSubmission(
            learner_id=user_id,
            concept_name=concept_name,
            resource_url="https://docs.python.org/3/library/trees.html",
            attempt_number=1,
            selected_answers={1: 3, 2: 3, 3: 3, 4: 3, 5: 3, 6: 3},  # Intentionally incorrect
            descriptive_answers={
                7: "I don't know the difference between preorder and inorder.",
                8: "Traversal is just visiting nodes.",
            },
        ),
    )

    # Check attempt count is 1
    assert agent.repo.count_quiz_attempts(user_id, concept_name) == 1

    # Now generate Attempt 2 (Retake)
    adaptive_quiz = agent.generate_quiz_for_resource(
        user_id=user_id,
        concept_name=concept_name,
        resource_url="https://docs.python.org/3/library/trees.html",
    )

    assert adaptive_quiz.attempt_number == 2
    assert adaptive_quiz.quiz_type == "adaptive_retake"
    assert len(adaptive_quiz.questions) == 10

    # Requirement 3: Predict Output coding questions must be present
    predict_output_questions = [
        q for q in adaptive_quiz.questions if q.question_type == QuestionType.PREDICT_OUTPUT
    ]
    assert len(predict_output_questions) >= 1, "Adaptive quiz must include Predict Output coding questions"
    for pq in predict_output_questions:
        assert pq.code_snippet is not None, "Predict Output questions must include code snippets"
        assert len(pq.code_snippet) > 10
        assert len(pq.options) == 4, "Predict Output questions must have 4 options"
        assert 0 <= pq.correct_option_index < 4

    # Requirement 3: Revision questions from previously mastered/seen concepts must be present
    revision_questions = [q for q in adaptive_quiz.questions if q.is_revision]
    assert len(revision_questions) >= 1, "Adaptive quiz must include revision retention questions"

    # Targeted questions must address weak concepts
    targeted_questions = [
        q for q in adaptive_quiz.questions
        if q.question_type == QuestionType.MCQ and not q.is_revision
    ]
    assert len(targeted_questions) >= 2


def test_remediation_efficacy_tracking(mock_agent):
    """Retaking a quiz after studying resources must measure improvement on weak areas."""
    agent = mock_agent
    user_id = "learner_004"

    agent.start_learning_journey(
        LearnerProfileCreate(
            user_id=user_id,
            name="David",
            learning_goal="Trees in DSA",
            current_level=DifficultyLevel.BEGINNER,
            preferred_format=LearningFormat.DOCUMENTATION,
            target_outcome="Understand tree traversals",
        )
    )

    concept_name = "Tree Fundamentals & Terminology"

    # Attempt 1: Poor score with weak areas
    eval_1 = agent.evaluate_quiz_and_remedy(
        user_id=user_id,
        submission=QuizSubmission(
            learner_id=user_id,
            concept_name=concept_name,
            resource_url="https://docs.python.org/3/library/trees.html",
            attempt_number=1,
            selected_answers={1: 3, 2: 3, 3: 3, 4: 3, 5: 3, 6: 3},
            descriptive_answers={7: "No idea", 8: "Not sure"},
        ),
    )
    assert len(eval_1.weak_areas) > 0
    assert eval_1.remediation_efficacy is None  # No prior attempt to compare

    # Attempt 2: Improved score with correct answers
    eval_2 = agent.evaluate_quiz_and_remedy(
        user_id=user_id,
        submission=QuizSubmission(
            learner_id=user_id,
            concept_name=concept_name,
            resource_url="https://docs.python.org/3/library/trees.html",
            attempt_number=2,
            selected_answers={1: 0, 2: 0, 3: 0, 4: 0, 5: 1, 6: 2},
            descriptive_answers={
                7: "A tree is hierarchical with a root and subtrees. Depth is distance from root while height is longest path to leaf.",
                8: "Binary trees have at most two children per node, distinguishing them from generic N-ary trees.",
                9: "Leaves are nodes without children.",
                10: "Root is the topmost node.",
            },
        ),
    )

    # Remediation efficacy must be evaluated
    assert eval_2.remediation_efficacy is not None
    assert "progress_percentage" in eval_2.remediation_efficacy
    assert "resolved_areas" in eval_2.remediation_efficacy
    assert len(eval_2.remediation_efficacy["resolved_areas"]) >= 1

    # Verify repository stores 2 attempts
    history = agent.repo.get_quiz_attempts(user_id, concept_name)
    assert len(history) == 2
    assert history[0].attempt_number == 1
    assert history[1].attempt_number == 2


def test_pedagogical_next_learning_action(mock_agent):
    """The agent must recommend PROCEED, REVISE, or REVISIT_PREREQUISITE based on performance and prerequisites."""
    agent = mock_agent
    user_id = "learner_005"

    agent.start_learning_journey(
        LearnerProfileCreate(
            user_id=user_id,
            name="Eva",
            learning_goal="Python Asynchronous Programming",
            current_level=DifficultyLevel.BEGINNER,
            preferred_format=LearningFormat.DOCUMENTATION,
            target_outcome="Async event loop",
        )
    )

    # 1. Prerequisite satisfied + High score -> PROCEED
    # Mark the foundational prerequisite 'Synchronous vs Asynchronous I/O Fundamentals' as mastered (0.85)
    agent.repo.upsert_concept_mastery(
        user_id,
        agent.repo.get_concept_masteries(user_id)["Synchronous vs Asynchronous I/O Fundamentals"].model_copy(update={"mastery_score": 0.85})
    )
    result_high = agent.evaluate_quiz_and_remedy(
        user_id=user_id,
        submission=QuizSubmission(
            learner_id=user_id,
            concept_name="Python Event Loop & Coroutines",
            resource_url="https://docs.python.org/3/library/asyncio.html",
            attempt_number=1,
            selected_answers={1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0},
            descriptive_answers={
                7: "The event loop on a single thread will yield and resume using non-blocking os selector epoll.",
                8: "Concurrency vs parallelism: cooperative multitasking on a single thread interleaving tasks vs multiple cores.",
                9: "In gather, exceptions bubble up unless return_exceptions prevents task failure from going unhandled.",
                10: "Manage connection pool using async with context manager to close and avoid socket leak.",
            },
        ),
    )
    assert result_high.next_action == NextLearningAction.PROCEED
    assert "proceed" in result_high.next_action_reason.lower()

    # 2. Moderate score (0.50) -> REVISE
    result_med = agent.evaluate_quiz_and_remedy(
        user_id=user_id,
        submission=QuizSubmission(
            learner_id=user_id,
            concept_name="Async Tasks & Gather",
            resource_url="https://docs.python.org/3/library/asyncio.html",
            attempt_number=1,
            selected_answers={1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 3},  # 5 MCQs correct out of 10 = 0.50
            descriptive_answers={},
        ),
    )
    assert result_med.next_action == NextLearningAction.REVISE
    assert "review" in result_med.next_action_reason.lower() or "retake" in result_med.next_action_reason.lower()

    # 3. High score on concept with UNMASTERED prerequisite (< 0.60) -> REVISIT_PREREQUISITE
    # Reset 'Synchronous vs Asynchronous I/O Fundamentals' prerequisite mastery to 0.25:
    agent.repo.upsert_concept_mastery(
        user_id,
        agent.repo.get_concept_masteries(user_id)["Synchronous vs Asynchronous I/O Fundamentals"].model_copy(update={"mastery_score": 0.25})
    )
    result_weak_prereq = agent.evaluate_quiz_and_remedy(
        user_id=user_id,
        submission=QuizSubmission(
            learner_id=user_id,
            concept_name="Python Event Loop & Coroutines",
            resource_url="https://docs.python.org/3/library/asyncio.html",
            attempt_number=2,
            selected_answers={1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0},
            descriptive_answers={
                7: "The event loop on a single thread will yield and resume using non-blocking os selector epoll.",
                8: "Concurrency vs parallelism: cooperative multitasking on a single thread interleaving tasks vs multiple cores.",
                9: "In gather, exceptions bubble up unless return_exceptions prevents task failure from going unhandled.",
                10: "Manage connection pool using async with context manager to close and avoid socket leak.",
            },
        ),
    )
    assert result_weak_prereq.next_action == NextLearningAction.REVISIT_PREREQUISITE
    assert "prerequisite" in result_weak_prereq.next_action_reason.lower()


def test_cognitive_memory_persistence_across_agent_reinstantiation(tmp_path):
    """Cognitive memory and quiz attempts must persist when a new agent instance connects to the same database."""
    db_file = str(tmp_path / "persistent_cognitive_memory.db")
    db_url = f"sqlite:///{db_file}"
    user_id = "persisted_learner"

    # Session 1: Create profile and complete quiz attempt 1
    agent_1 = LearningAgent(db_url=db_url)
    mock_agent_dependencies(agent_1)

    agent_1.start_learning_journey(
        LearnerProfileCreate(
            user_id=user_id,
            name="Frank",
            learning_goal="Tree Traversal Algorithms",
            current_level=DifficultyLevel.BEGINNER,
            preferred_format=LearningFormat.DOCUMENTATION,
            target_outcome="Master recursive and iterative traversals",
        )
    )

    eval_session1 = agent_1.evaluate_quiz_and_remedy(
        user_id=user_id,
        submission=QuizSubmission(
            learner_id=user_id,
            concept_name="Tree Inorder & Postorder",
            resource_url="https://docs.python.org/3/library/trees.html",
            attempt_number=1,
            selected_answers={1: 3, 2: 3, 3: 0, 4: 0, 5: 0, 6: 0},
            descriptive_answers={7: "Inorder visits left root right.", 8: ""},
        ),
    )
    assert eval_session1.attempt_number == 1

    # Session 2: Fresh LearningAgent instance with the same database
    agent_2 = LearningAgent(db_url=db_url)
    mock_agent_dependencies(agent_2)

    # Verify history is loaded
    history = agent_2.repo.get_quiz_attempts(user_id=user_id, concept_name="Tree Inorder & Postorder")
    assert len(history) == 1
    assert history[0].attempt_number == 1
    assert history[0].score == eval_session1.score

    # Verify cognitive profile persists
    profile = agent_2.repo.get_learner(user_id)
    assert profile is not None
    assert profile.name == "Frank"

    # Attempt 2 generated by agent_2 should detect past attempt and generate adaptive retake
    quiz_attempt2 = agent_2.generate_quiz_for_resource(
        user_id=user_id,
        concept_name="Tree Inorder & Postorder",
        resource_url="https://docs.python.org/3/library/trees.html",
    )
    assert quiz_attempt2.attempt_number == 2
    assert quiz_attempt2.quiz_type == "adaptive_retake"


def test_unique_questions_across_all_subtopics(mock_agent):
    """Verifies that all 5 subtopics from the roadmap produce their own distinct diagnostic questions."""
    agent = mock_agent
    user_id = "diversity_tester"

    agent.start_learning_journey(
        LearnerProfileCreate(
            user_id=user_id,
            name="Grace",
            learning_goal="Tree Master",
            current_level=DifficultyLevel.BEGINNER,
            preferred_format=LearningFormat.DOCUMENTATION,
            target_outcome="Trees",
        )
    )

    subtopics = [
        "Tree Fundamentals and Terminology",
        "Binary Tree Representation and Traversals",
        "Binary Search Trees (BST) and Operations",
        "Balanced Binary Trees and Rotations",
        "Tree Problem-Solving Patterns and Applications",
    ]

    quizzes = {}
    for sub in subtopics:
        q = agent.generate_quiz_for_resource(
            user_id=user_id,
            concept_name=sub,
            resource_url=f"https://docs.python.org/3/library/{sub.replace(' ', '')}.html",
        )
        assert q is not None
        assert len(q.questions) == 10
        quizzes[sub] = q

    # Collect first question text from each subtopic
    first_q_texts = [quizzes[sub].questions[0].question_text for sub in subtopics]
    # Ensure all first questions are completely unique
    assert len(set(first_q_texts)) == len(subtopics), f"Questions overlapped! {first_q_texts}"

    # Verify Predict Output coding questions are present in each subtopic quiz
    for sub, q in quizzes.items():
        coding_qs = [item for item in q.questions if item.question_type == QuestionType.PREDICT_OUTPUT]
        assert len(coding_qs) >= 2, f"Subtopic '{sub}' should have Predict Output coding questions"
        for cq in coding_qs:
            assert cq.code_snippet is not None and len(cq.code_snippet) > 0
            assert len(cq.options) == 4

