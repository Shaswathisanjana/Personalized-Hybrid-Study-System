"""Agent Re-planning: Adaptive path restructuring based on evolving cognitive state."""

import logging
from typing import List, Dict, Optional

from cognitive_learning_agent.memory.repository import CognitiveMemoryRepository
from cognitive_learning_agent.cognitive_engine.prerequisite_graph import PrerequisiteGraph
from cognitive_learning_agent.discovery.searcher import ResourceSearcher
from cognitive_learning_agent.discovery.extractor import PageExtractor
from cognitive_learning_agent.discovery.validator import LinkValidator
from cognitive_learning_agent.discovery.ranker import ResourceRanker
from cognitive_learning_agent.models.schemas import (
    LearningPath,
    LearningResource,
    AssessmentFeedback,
    ReplanResult,
    CognitiveConflict,
    MisconceptionItem,
    DifficultyLevel,
    LearningFormat,
    ConceptStatus,
)

logger = logging.getLogger(__name__)


class AgentReplanner:
    """Dynamically re-evaluates student progress, adjusts difficulty, and re-sequences the learning path."""

    def __init__(
        self,
        repository: CognitiveMemoryRepository,
        searcher: ResourceSearcher,
        extractor: PageExtractor,
        validator: LinkValidator,
        ranker: ResourceRanker,
    ):
        self.repository = repository
        self.searcher = searcher
        self.extractor = extractor
        self.validator = validator
        self.ranker = ranker

    def replan(
        self,
        user_id: str,
        current_path: LearningPath,
        latest_feedback: Optional[AssessmentFeedback] = None,
        detected_conflicts: Optional[List[CognitiveConflict]] = None,
        active_misconceptions: Optional[List[MisconceptionItem]] = None,
    ) -> ReplanResult:
        """Re-examine cognitive state and adapt learning path recommendations."""
        learner = self.repository.get_learner(user_id)
        if not learner:
            raise ValueError(f"Learner {user_id} not found.")

        masteries = self.repository.get_concept_masteries(user_id)
        prereqs = self.repository.get_prerequisites(user_id)
        graph = PrerequisiteGraph(prereqs)
        for c in current_path.ordered_concepts:
            graph.add_concept(c)

        reasons = []
        actions = []

        # 1. Check for Active Misconceptions
        active_misc = active_misconceptions or self.repository.get_active_misconceptions(user_id)
        misconception_concepts = {m.concept_name for m in active_misc}

        # 2. Check for Low Performance or Struggle
        struggling_concept = None
        if latest_feedback:
            c_name = latest_feedback.concept_name
            if (latest_feedback.quiz_score is not None and latest_feedback.quiz_score < 0.50) or latest_feedback.perceived_difficulty == "too_hard" or latest_feedback.confusion_reported:
                struggling_concept = c_name
                reasons.append(
                    f"Learner struggled on '{c_name}' (quiz: {round(latest_feedback.quiz_score * 100) if latest_feedback.quiz_score is not None else 'N/A'}%, difficulty: {latest_feedback.perceived_difficulty})."
                )

        # 3. Check for Conflicts
        conflicts = detected_conflicts or []
        for conf in conflicts:
            reasons.append(f"Cognitive Conflict: {conf.description}")
            actions.append(f"Action: {conf.resolution_action}")

        # 4. Determine Gaps and Sequence
        topological_order = graph.topological_sort()
        remaining_concepts = []

        for c in topological_order:
            m = masteries.get(c)
            # If not yet proficient (< 0.70) or has active misconception, keep in learning path
            if m is None or m.mastery_score < 0.70 or c in misconception_concepts:
                remaining_concepts.append(c)

        # 5. Adapt Learning Resources
        adapted_resources: List[LearningResource] = []
        seen_urls = set()

        # Prioritize Remediation if struggling
        if struggling_concept:
            unmastered_prereqs = graph.get_unmastered_prerequisites(struggling_concept, masteries)
            if unmastered_prereqs:
                remedial_target = unmastered_prereqs[0]
                actions.append(f"Injected prerequisite remediation for '{remedial_target}' before '{struggling_concept}'.")
                rem_resources = self._discover_for_concept(
                    concept_name=remedial_target,
                    goal=learner.learning_goal,
                    format_pref=LearningFormat.VISUALIZATION if learner.preferred_format == LearningFormat.ANY else learner.preferred_format,
                    difficulty=DifficultyLevel.BEGINNER,
                    preferred_language=learner.preferred_language or "Python",
                )
                for r in rem_resources[:1]:
                    if r.url not in seen_urls:
                        r.target_concept = remedial_target
                        r.snippet = f"[Prerequisite Remediation] {r.snippet}"
                        adapted_resources.append(r)
                        seen_urls.add(r.url)
                        break

            # Also provide alternative format for struggling concept (e.g. video / visual guide)
            alt_format = LearningFormat.VIDEO if learner.preferred_format != LearningFormat.VIDEO else LearningFormat.VISUALIZATION
            actions.append(f"Adjusted difficulty to Beginner & prioritized alternative format ({alt_format.value}) for '{struggling_concept}'.")
            alt_resources = self._discover_for_concept(
                concept_name=struggling_concept,
                goal=learner.learning_goal,
                format_pref=alt_format,
                difficulty=DifficultyLevel.BEGINNER,
                preferred_language=learner.preferred_language or "Python",
            )
            for r in alt_resources[:1]:
                if r.url not in seen_urls:
                    r.target_concept = struggling_concept
                    r.snippet = f"[Stepped-down Alternative] {r.snippet}"
                    adapted_resources.append(r)
                    seen_urls.add(r.url)
                    break

        # Retain or append uncompleted resources from current path for remaining concepts (strictly 1 distinct resource per concept)
        seen_concepts = {r.target_concept for r in adapted_resources}
        for c in remaining_concepts:
            if c in seen_concepts:
                continue
            # Check existing resources for concept c
            existing = [r for r in current_path.resources if r.target_concept == c and r.url not in seen_urls]
            if existing:
                for r in existing[:1]:
                    adapted_resources.append(r)
                    seen_urls.add(r.url)
                    seen_concepts.add(c)
                    break
            else:
                # Discover new resources for this gap
                discovered = self._discover_for_concept(
                    concept_name=c,
                    goal=learner.learning_goal,
                    format_pref=learner.preferred_format,
                    difficulty=learner.current_level,
                    preferred_language=learner.preferred_language or "Python",
                )
                for r in discovered[:1]:
                    if r.url not in seen_urls:
                        adapted_resources.append(r)
                        seen_urls.add(r.url)
                        seen_concepts.add(c)
                        break

        # Recalculate total estimated time
        total_time = sum(r.estimated_minutes for r in adapted_resources)

        updated_path = LearningPath(
            learner_id=user_id,
            goal=learner.learning_goal,
            target_outcome=learner.target_outcome,
            resources=adapted_resources,
            ordered_concepts=remaining_concepts,
            rationale=(
                f"Adapted path for {learner.name}. Addressed {len(reasons)} cognitive signals. "
                f"Remaining concepts to achieve target outcome: {', '.join(remaining_concepts)}."
            ),
            estimated_total_minutes=total_time,
        )

        return ReplanResult(
            replan_triggered=bool(reasons or actions),
            reasons=reasons if reasons else ["Regular progression update."],
            actions_taken=actions if actions else ["Retained current sequence; progression on track."],
            updated_learning_path=updated_path,
            conflicts_detected=conflicts,
            active_misconceptions=active_misc,
        )

    def _discover_for_concept(
        self,
        concept_name: str,
        goal: str,
        format_pref: LearningFormat,
        difficulty: DifficultyLevel,
        preferred_language: str,
    ) -> List[LearningResource]:
        """Discover, validate, and rank resources for a concept quickly."""
        raw_items = self.searcher.search_for_concept(
            concept_name=concept_name,
            goal=goal,
            preferred_format=format_pref,
            difficulty=difficulty,
            preferred_language=preferred_language,
        )
        validated = self.validator.validate_and_deduplicate(raw_items)
        ranked = self.ranker.rank_resources(
            candidate_items=validated,
            target_concept=concept_name,
            learning_goal=goal,
            learner_level=difficulty,
            preferred_format=format_pref,
        )
        return ranked
