"""Conflict Detector and Resolver: Contradiction analysis and cognitive calibration."""

import logging
from typing import List, Optional

from cognitive_learning_agent.config import settings
from cognitive_learning_agent.memory.repository import CognitiveMemoryRepository
from cognitive_learning_agent.models.schemas import (
    CognitiveConflict,
    ConflictSeverity,
    AssessmentFeedback,
    DifficultyLevel,
)

logger = logging.getLogger(__name__)


class ConflictDetectorResolver:
    """Detects discrepancies between claimed proficiency and observed behavior, then resolves them."""

    def __init__(self, repository: CognitiveMemoryRepository):
        self.repository = repository
        self.penalty = settings.CONFLICT_CONFIDENCE_PENALTY

    def detect_and_resolve(self, feedback: AssessmentFeedback) -> List[CognitiveConflict]:
        """Inspect learner actions and cognitive state for contradictions."""
        conflicts: List[CognitiveConflict] = []
        user_id = feedback.learner_id
        concept_name = feedback.concept_name

        learner = self.repository.get_learner(user_id)
        if not learner:
            return conflicts

        masteries = self.repository.get_concept_masteries(user_id)
        current_mastery = masteries.get(concept_name)
        prereqs = self.repository.get_prerequisites(user_id)

        # -------------------------------------------------------------
        # Conflict 1: Claimed vs Measured Performance
        # -------------------------------------------------------------
        if feedback.quiz_score is not None:
            claimed_level = learner.current_level
            if claimed_level == DifficultyLevel.ADVANCED and feedback.quiz_score < 0.40:
                conflict = CognitiveConflict(
                    concept_name=concept_name,
                    severity=ConflictSeverity.HIGH,
                    description=(
                        f"Student profile claims Advanced competency, but scored only "
                        f"{round(feedback.quiz_score * 100)}% on {concept_name} assessment."
                    ),
                    claimed_mastery=0.90,
                    observed_performance=feedback.quiz_score,
                    resolution_action="Penalize concept confidence and insert foundational diagnostic tutorial.",
                )
                conflicts.append(conflict)
                self._apply_confidence_penalty(user_id, concept_name)

            elif current_mastery and current_mastery.mastery_score > 0.70 and feedback.quiz_score < 0.45:
                conflict = CognitiveConflict(
                    concept_name=concept_name,
                    severity=ConflictSeverity.MEDIUM,
                    description=(
                        f"Prior concept mastery was high ({round(current_mastery.mastery_score * 100)}%), "
                        f"but recent quiz dropped to {round(feedback.quiz_score * 100)}%."
                    ),
                    claimed_mastery=current_mastery.mastery_score,
                    observed_performance=feedback.quiz_score,
                    resolution_action="Degrade confidence score and prompt concept refresher.",
                )
                conflicts.append(conflict)
                self._apply_confidence_penalty(user_id, concept_name)

        # -------------------------------------------------------------
        # Conflict 2: Prerequisite Inversion
        # -------------------------------------------------------------
        # Check if concept has unmastered prerequisites
        concept_prereqs = [p.prerequisite_name for p in prereqs if p.concept_name == concept_name]
        for p_name in concept_prereqs:
            p_mastery = masteries.get(p_name)
            if p_mastery is None or p_mastery.mastery_score < 0.35:
                if feedback.quiz_score is not None and feedback.quiz_score < 0.50:
                    conflict = CognitiveConflict(
                        concept_name=concept_name,
                        severity=ConflictSeverity.HIGH,
                        description=(
                            f"Student attempted assessment for {concept_name} while prerequisite "
                            f"'{p_name}' has deficient mastery ({round((p_mastery.mastery_score if p_mastery else 0.0) * 100)}%)."
                        ),
                        claimed_mastery=current_mastery.mastery_score if current_mastery else 0.0,
                        observed_performance=feedback.quiz_score,
                        resolution_action=f"Mandate remediation on prerequisite '{p_name}' before proceeding.",
                    )
                    conflicts.append(conflict)

        # -------------------------------------------------------------
        # Conflict 3: Difficulty Discordance
        # -------------------------------------------------------------
        if feedback.perceived_difficulty == "too_hard" and learner.current_level == DifficultyLevel.ADVANCED:
            conflict = CognitiveConflict(
                concept_name=concept_name,
                severity=ConflictSeverity.LOW,
                description=(
                    f"Advanced learner reported introductory resource on {concept_name} as 'too_hard'."
                ),
                claimed_mastery=0.85,
                observed_performance=0.30,
                resolution_action="Calibrate profile difficulty setting to intermediate.",
            )
            conflicts.append(conflict)

        return conflicts

    def _apply_confidence_penalty(self, user_id: str, concept_name: str):
        """Decrease confidence in mastery when contradiction is detected."""
        masteries = self.repository.get_concept_masteries(user_id)
        item = masteries.get(concept_name)
        if item:
            item.confidence_score = max(0.15, round(item.confidence_score - self.penalty, 3))
            item.notes = (item.notes or "") + " [Confidence penalized due to performance contradiction]"
            self.repository.upsert_concept_mastery(user_id, item)
            logger.info(f"Applied confidence penalty to {concept_name} for user {user_id}")
