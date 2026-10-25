"""Misconception Manager: Diagnosis, tracking, and resolution of cognitive misconceptions."""

import logging
from datetime import datetime
from typing import List, Optional

from cognitive_learning_agent.memory.repository import CognitiveMemoryRepository
from cognitive_learning_agent.models.schemas import (
    MisconceptionItem,
    MisconceptionStatus,
    AssessmentFeedback,
)
from cognitive_learning_agent.llm.client import LLMClient

logger = logging.getLogger(__name__)


class MisconceptionManager:
    """Detects, persists, and monitors resolution of learner misconceptions."""

    def __init__(self, repository: CognitiveMemoryRepository, llm_client: Optional[LLMClient] = None):
        self.repository = repository
        self.llm = llm_client or LLMClient()

    def process_feedback(self, feedback: AssessmentFeedback) -> Optional[MisconceptionItem]:
        """Analyze assessment feedback for potential misconceptions and record or resolve them."""
        user_id = feedback.learner_id
        concept_name = feedback.concept_name

        # 1. Check if learner already has active misconceptions on this concept
        active_items = self.repository.get_active_misconceptions(user_id, concept_name)

        # 2. Check for Resolution: if learner now scored high on quiz (>= 0.75), rectify active misconceptions!
        if active_items and feedback.quiz_score is not None and feedback.quiz_score >= 0.75:
            for item in active_items:
                if item.id:
                    self.repository.resolve_misconception(
                        item.id,
                        notes=f"Resolved via successful assessment score: {round(feedback.quiz_score * 100, 1)}%",
                    )
                    logger.info(f"Resolved misconception {item.id} for {concept_name}")
            return None

        # 3. Check for New Misconception Trigger
        needs_diagnosis = (
            feedback.confusion_reported
            or (feedback.quiz_score is not None and feedback.quiz_score < 0.50)
            or feedback.perceived_difficulty == "too_hard"
        )

        if not needs_diagnosis:
            return None

        # Avoid spamming duplicates if an active misconception already exists for this concept
        if active_items:
            return active_items[0]

        # 4. Run Diagnostic Engine (LLM or Heuristic)
        diagnosis = self.llm.diagnose_misconception(
            concept_name=concept_name,
            quiz_score=feedback.quiz_score,
            perceived_difficulty=feedback.perceived_difficulty,
            reported_confusion=feedback.confusion_reported,
            notes=feedback.notes,
        )

        if diagnosis.get("has_misconception"):
            misc_text = diagnosis.get("misconception_text") or f"Struggles with core execution of {concept_name}"
            new_misc = MisconceptionItem(
                learner_id=user_id,
                concept_name=concept_name,
                description=misc_text,
                evidence_observation=(
                    f"Triggered by quiz_score={feedback.quiz_score}, "
                    f"difficulty={feedback.perceived_difficulty}, "
                    f"notes='{feedback.notes or 'None'}'"
                ),
                status=MisconceptionStatus.ACTIVE,
                detected_at=datetime.utcnow(),
            )
            saved = self.repository.add_misconception(new_misc)
            logger.info(f"Recorded active misconception for learner {user_id} on {concept_name}: {misc_text}")
            return saved

        return None

    def get_active_misconceptions(self, user_id: str) -> List[MisconceptionItem]:
        """Retrieve all currently unresolved misconceptions for learner."""
        return self.repository.get_active_misconceptions(user_id)

    def resolve_misconception_manually(self, misconception_id: int, notes: str) -> Optional[MisconceptionItem]:
        """Manually mark a misconception as rectified."""
        return self.repository.resolve_misconception(misconception_id, notes=notes)
