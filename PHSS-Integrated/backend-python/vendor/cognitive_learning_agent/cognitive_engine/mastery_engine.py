"""Mastery Engine: Evidence-based Bayesian / EWMA mastery and confidence calculation."""

import logging
import math
from datetime import datetime
from typing import List, Dict, Optional

from cognitive_learning_agent.config import settings
from cognitive_learning_agent.memory.repository import CognitiveMemoryRepository
from cognitive_learning_agent.models.schemas import (
    ConceptMasteryItem,
    ConceptStatus,
    EvidenceItem,
    EvidenceType,
)

logger = logging.getLogger(__name__)


class MasteryEngine:
    """Computes concept mastery and confidence based strictly on verified learning evidence."""

    WEIGHTS = {
        EvidenceType.QUIZ: 1.0,
        EvidenceType.PRACTICE: 0.9,
        EvidenceType.CONFUSION_REPORT: 0.8,
        EvidenceType.COMPLETION: 0.5,
        EvidenceType.SELF_RATING: 0.4,
    }

    def __init__(self, repository: CognitiveMemoryRepository):
        self.repository = repository
        self.proficiency_threshold = settings.PROFICIENCY_THRESHOLD
        self.mastery_threshold = settings.MASTERY_THRESHOLD
        self.min_evidence_for_mastery = settings.MIN_EVIDENCE_FOR_MASTERY

    def update_concept_mastery(self, user_id: str, concept_name: str) -> ConceptMasteryItem:
        """Recalculate mastery score, confidence, and status for a concept from accumulated evidence."""
        evidence_items = self.repository.get_evidence_for_concept(user_id, concept_name)

        if not evidence_items:
            # No evidence yet
            existing = self.repository.get_concept_masteries(user_id).get(concept_name)
            if existing:
                return existing
            item = ConceptMasteryItem(
                concept_name=concept_name,
                mastery_score=0.0,
                confidence_score=0.1,
                status=ConceptStatus.NOT_STARTED,
                evidence_count=0,
                last_evaluated_at=datetime.utcnow(),
            )
            return self.repository.upsert_concept_mastery(user_id, item)

        # 1. Evidence aggregation with recency and type weighting
        weighted_scores = []
        total_weight = 0.0
        quiz_scores = []

        # Chronological order (oldest to newest)
        sorted_evidence = sorted(evidence_items, key=lambda e: e.timestamp)

        for i, ev in enumerate(sorted_evidence):
            if ev.score is None:
                continue

            base_weight = self.WEIGHTS.get(ev.evidence_type, 0.5)
            # Recency factor: later evidence receives up to 1.5x weight
            recency_mult = 1.0 + (i / max(1, len(sorted_evidence))) * 0.5
            eff_weight = base_weight * recency_mult

            weighted_scores.append(ev.score * eff_weight)
            total_weight += eff_weight

            if ev.evidence_type in (EvidenceType.QUIZ, EvidenceType.PRACTICE):
                quiz_scores.append(ev.score)

        if total_weight > 0:
            raw_mastery = sum(weighted_scores) / total_weight
        else:
            raw_mastery = 0.0

        mastery_score = max(0.0, min(1.0, round(raw_mastery, 3)))

        # 2. Confidence Calculation
        # C = 1 - exp(-0.4 * effective_evidence_count)
        # Bounded between 0.15 and 0.98
        n_effective = len(evidence_items)
        confidence = 1.0 - math.exp(-0.45 * n_effective)
        # Penalize confidence if quiz score has high variance or recent failure
        if quiz_scores and quiz_scores[-1] < 0.4 and mastery_score > 0.6:
            confidence = max(0.2, confidence - 0.25)
        confidence = max(0.10, min(0.98, round(confidence, 3)))

        # 3. Status Determination (Strict empirical threshold)
        status = self._determine_status(mastery_score, confidence, len(evidence_items), quiz_scores)

        # 4. Save and return updated concept mastery
        item = ConceptMasteryItem(
            concept_name=concept_name,
            mastery_score=mastery_score,
            confidence_score=confidence,
            status=status,
            evidence_count=len(evidence_items),
            last_evaluated_at=datetime.utcnow(),
            notes=f"Evaluated from {len(evidence_items)} evidence items (latest quiz: {quiz_scores[-1] if quiz_scores else 'None'}).",
        )
        return self.repository.upsert_concept_mastery(user_id, item)

    def _determine_status(
        self,
        mastery_score: float,
        confidence: float,
        evidence_count: int,
        quiz_scores: List[float],
    ) -> ConceptStatus:
        """Enforces the invariant: Never claim mastery without sufficient empirical evidence.
        Any concept with recorded learning evidence or quiz attempts is IN_PROGRESS.
        """
        if evidence_count == 0:
            return ConceptStatus.NOT_STARTED

        # Mastery requires high score, high confidence, minimum evidence items, and verified quiz performance
        has_high_quiz = any(s >= 0.82 for s in quiz_scores) if quiz_scores else False
        if (
            mastery_score >= self.mastery_threshold
            and confidence >= 0.70
            and evidence_count >= self.min_evidence_for_mastery
            and has_high_quiz
        ):
            return ConceptStatus.MASTERED

        # Proficiency requires solid score with at least some assessment evidence
        if mastery_score >= self.proficiency_threshold and evidence_count >= 2:
            return ConceptStatus.PROFICIENT

        return ConceptStatus.IN_PROGRESS
