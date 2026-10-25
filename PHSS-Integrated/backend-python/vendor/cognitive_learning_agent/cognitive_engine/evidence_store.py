"""Evidence Store: Ingestion, querying, and aggregation of atomic learning observations."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from cognitive_learning_agent.memory.repository import CognitiveMemoryRepository
from cognitive_learning_agent.models.schemas import (
    EvidenceItem,
    EvidenceType,
    AssessmentFeedback,
)

logger = logging.getLogger(__name__)


class EvidenceStore:
    """Manages the persistence and aggregation of atomic cognitive learning observations."""

    def __init__(self, repository: CognitiveMemoryRepository):
        self.repository = repository

    def record_feedback(self, feedback: AssessmentFeedback) -> List[EvidenceItem]:
        """Convert a user's feedback/assessment into discrete atomic evidence items."""
        items_recorded = []

        # 1. Resource completion evidence
        if feedback.completed:
            ev_comp = EvidenceItem(
                learner_id=feedback.learner_id,
                concept_name=feedback.concept_name,
                evidence_type=EvidenceType.COMPLETION,
                score=0.65 if feedback.quiz_score is None else None,
                resource_url=feedback.resource_url,
                observation=f"Completed resource: {feedback.resource_url or 'practice item'}",
                user_feedback_rating=feedback.usefulness_rating,
                timestamp=datetime.utcnow(),
            )
            items_recorded.append(self.repository.add_evidence(ev_comp))

        # 2. Quiz / Performance evidence
        if feedback.quiz_score is not None:
            ev_quiz = EvidenceItem(
                learner_id=feedback.learner_id,
                concept_name=feedback.concept_name,
                evidence_type=EvidenceType.QUIZ,
                score=float(feedback.quiz_score),
                resource_url=feedback.resource_url,
                observation=f"Assessment score: {round(feedback.quiz_score * 100, 1)}%",
                user_feedback_rating=feedback.usefulness_rating,
                timestamp=datetime.utcnow(),
            )
            items_recorded.append(self.repository.add_evidence(ev_quiz))

        # 3. Self-rating & perceived difficulty evidence
        if feedback.perceived_difficulty:
            score_map = {"too_easy": 0.85, "just_right": 0.70, "too_hard": 0.30}
            ev_diff = EvidenceItem(
                learner_id=feedback.learner_id,
                concept_name=feedback.concept_name,
                evidence_type=EvidenceType.SELF_RATING,
                score=score_map.get(feedback.perceived_difficulty, 0.60),
                resource_url=feedback.resource_url,
                observation=f"Perceived difficulty: {feedback.perceived_difficulty}. Usefulness rating: {feedback.usefulness_rating}/5",
                user_feedback_rating=feedback.usefulness_rating,
                timestamp=datetime.utcnow(),
            )
            items_recorded.append(self.repository.add_evidence(ev_diff))

        # 4. Confusion report evidence
        if feedback.confusion_reported or (feedback.notes and "confus" in feedback.notes.lower()):
            ev_conf = EvidenceItem(
                learner_id=feedback.learner_id,
                concept_name=feedback.concept_name,
                evidence_type=EvidenceType.CONFUSION_REPORT,
                score=0.20,
                resource_url=feedback.resource_url,
                observation=f"Reported confusion: {feedback.notes or 'Student indicated struggle with concept'}",
                user_feedback_rating=feedback.usefulness_rating,
                timestamp=datetime.utcnow(),
            )
            items_recorded.append(self.repository.add_evidence(ev_conf))

        # Also log to learning history
        if feedback.resource_url:
            self.repository.record_history(
                user_id=feedback.learner_id,
                resource_url=feedback.resource_url,
                title=f"Learning material on {feedback.concept_name}",
                completed=feedback.completed,
                perceived_difficulty=feedback.perceived_difficulty,
                usefulness_rating=feedback.usefulness_rating,
            )

        return items_recorded

    def get_concept_evidence(self, user_id: str, concept_name: str) -> List[EvidenceItem]:
        """Fetch all evidence recorded for a specific concept."""
        return self.repository.get_evidence_for_concept(user_id, concept_name)

    def get_recent_evidence(self, user_id: str, limit: int = 20) -> List[EvidenceItem]:
        """Fetch chronologically recent evidence items."""
        return self.repository.get_recent_evidence(user_id, limit=limit)
