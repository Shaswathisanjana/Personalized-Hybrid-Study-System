"""Command Line Interface (CLI) for Cognitive Learning Agent."""

import sys
import argparse
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from cognitive_learning_agent.core.agent import LearningAgent
from cognitive_learning_agent.models.schemas import (
    LearnerProfileCreate,
    DifficultyLevel,
    LearningFormat,
    AssessmentFeedback,
)


# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def run_demo():
    print("=" * 70)
    print("[COGNITIVE LEARNING AGENT] (Zero Content Generation)")
    print("=" * 70)

    agent = LearningAgent()

    user_id = "cli_learner_01"
    goal = "Master Python asyncio and concurrency for scalable network applications"
    target_outcome = "Build a high-performance asynchronous web scraper"
    level = DifficultyLevel.BEGINNER
    preferred_format = LearningFormat.ANY

    print(f"\n[Step 1 & 2] Ingesting Goal and Initializing Cognitive State...")
    print(f"Goal: {goal}")
    print(f"Target Outcome: {target_outcome}")
    print(f"Initial Level: {level.value}")

    profile_input = LearnerProfileCreate(
        user_id=user_id,
        name="Alex",
        learning_goal=goal,
        current_level=level,
        preferred_format=preferred_format,
        target_outcome=target_outcome,
        preferred_language="Python",
    )

    profile, path = agent.start_learning_journey(profile_input)

    print(f"\n[Step 3 & 4] Recommended Learning Path ({len(path.resources)} Validated Resources):")
    print(f"Curriculum Rationale: {path.rationale}")
    print("-" * 70)
    for i, res in enumerate(path.resources, 1):
        print(f" {i}. [{res.format.value.upper()}] {res.title}")
        print(f"    Concept: {res.target_concept} | Difficulty: {res.difficulty.value} | Est: {res.estimated_minutes} min")
        print(f"    URL: {res.url}")
        print(f"    Relevance: {res.relevance_score}")
        print()

    # Step 5: Diagnostic Quiz, Weak Area Diagnosis & Remedial Resources
    item_1 = path.resources[0]
    print("=" * 70)
    print(f"[Step 5 & 6] Generating Concept Diagnostic Quiz for Item 1: '{item_1.target_concept}'...")
    quiz = agent.generate_quiz_for_resource(user_id, item_1.target_concept, item_1.url)
    print(f"Quiz Generated with {len(quiz.questions)} questions:")
    for q in quiz.questions:
        print(f"  Q{q.question_id}: {q.question_text}")
        print(f"     Aspect: {q.concept_aspect}")
        for opt_idx, opt in enumerate(q.options):
            print(f"     [{opt_idx}] {opt}")

    print("\nSimulating learner submitting answers (Q1: distractor revealing misconception, Q2: correct)...")
    from cognitive_learning_agent.models.schemas import QuizSubmission
    sub = QuizSubmission(
        learner_id=user_id,
        concept_name=item_1.target_concept,
        resource_url=item_1.url,
        selected_answers={
            quiz.questions[0].question_id: 1,  # distractor revealing misconception
            quiz.questions[1].question_id: quiz.questions[1].correct_option_index,
        } if len(quiz.questions) >= 2 else {quiz.questions[0].question_id: 1},
    )

    eval_result = agent.evaluate_quiz_and_remedy(sub)
    print(f"Quiz Score: {round(eval_result.score * 100)}% ({eval_result.correct_count}/{eval_result.total_questions})")
    print(f"Weak Areas Diagnosed: {eval_result.weak_areas}")
    print(f"Misconceptions Identified: {eval_result.detected_misconceptions}")

    print(f"\n[Remediation] Recommending Targeted Online Resources Covering Weak Areas ({len(eval_result.targeted_resources)} Found):")
    for r_idx, rem in enumerate(eval_result.targeted_resources, 1):
        print(f"  {r_idx}. [{rem.target_concept}] {rem.title}")
        print(f"     URL: {rem.url}")
        print(f"     Format: {rem.format.value} | Domain: {rem.domain}")
        print(f"     Relevance: {round(rem.relevance_score * 100)}%")

    # Inspect updated cognitive state
    snapshot1 = agent.get_cognitive_state(user_id)
    c_mastery = snapshot1.concepts.get(item_1.target_concept)
    if c_mastery:
        print(f" -> Concept Mastery: {round(c_mastery.mastery_score * 100, 1)}% (Status: {c_mastery.status.value}, Confidence: {round(c_mastery.confidence_score * 100, 1)}%)")

    # Step 7: Simulate Struggle & Misconception on Item 2
    if len(path.resources) > 1:
        item_2 = path.resources[1]
        print("\n" + "=" * 70)
        print(f"[Step 5 & 6] Submitting Evidence for Item 2: '{item_2.target_concept}'...")
        print("Simulated Feedback: Quiz Score = 30%, Difficulty = 'too_hard', Confusion = TRUE")
        print("Notes: 'I thought asyncio runs multiple CPU threads in parallel.'")
        fb2 = AssessmentFeedback(
            learner_id=user_id,
            concept_name=item_2.target_concept,
            resource_url=item_2.url,
            completed=True,
            quiz_score=0.30,
            perceived_difficulty="too_hard",
            usefulness_rating=2,
            confusion_reported=True,
            notes="I thought asyncio runs multiple CPU threads in parallel.",
        )
        replan2 = agent.process_feedback(fb2)

        print("\n" + "=" * 70)
        print("[Step 7] Adaptive Re-planning Triggered!")
        print(f"Reasons: {replan2.reasons}")
        print(f"Actions Taken: {replan2.actions_taken}")
        if replan2.active_misconceptions:
            print(f"Active Misconception: {replan2.active_misconceptions[0].description}")

        print("\nUpdated Adapted Learning Path Resources:")
        for idx, res in enumerate(replan2.updated_learning_path.resources, 1):
            print(f" {idx}. {res.title}")
            print(f"    Concept: {res.target_concept} | Format: {res.format.value} | URL: {res.url}")

    print("\n" + "=" * 70)
    print("Demo completed successfully!")


if __name__ == "__main__":
    run_demo()
