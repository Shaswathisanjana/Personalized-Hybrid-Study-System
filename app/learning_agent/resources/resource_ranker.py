import math
import re

from app.learning_agent.resources.models import (
    LearningResource,
    RankedLearningResource,
)


class LearningResourceRanker:
    """
    Personalized ranking component for learning resources.

    This component does NOT call an LLM.

    Ranking happens in two stages:

    STAGE 1:
        Relevance filtering

    STAGE 2:
        Personalized ranking using:
        - topic relevance
        - difficulty match
        - resource quality

    This prevents an irrelevant but popular resource
    from outranking a genuinely relevant educational
    resource.

    Current thresholds and weights are project
    heuristics and should later be experimentally
    evaluated and calibrated.
    """

    DIFFICULTY_VALUE = {
        "easy": 1,
        "medium": 2,
        "hard": 3,
    }

    def __init__(
        self,
        relevance_weight: float = 0.50,
        difficulty_weight: float = 0.30,
        quality_weight: float = 0.20,
        minimum_relevance: float = 0.30,
    ):

        total = (
            relevance_weight
            + difficulty_weight
            + quality_weight
        )

        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                "Ranking weights must sum to 1.0."
            )

        if not 0.0 <= minimum_relevance <= 1.0:
            raise ValueError(
                "minimum_relevance must be between "
                "0.0 and 1.0."
            )

        self.relevance_weight = relevance_weight
        self.difficulty_weight = difficulty_weight
        self.quality_weight = quality_weight

        self.minimum_relevance = minimum_relevance

    # ==================================================
    # PUBLIC RANKING METHOD
    # ==================================================

    def rank(
        self,
        concept_name: str,
        student_level: str,
        resources: list[LearningResource],
    ) -> list[RankedLearningResource]:
        """
        Filter and rank candidate resources.

        Resources that fail the minimum topic-relevance
        requirement are removed BEFORE personalization.

        Higher final_score means a stronger recommendation.
        """

        concept_name = concept_name.strip()
        student_level = student_level.strip().lower()

        if not concept_name:
            raise ValueError(
                "concept_name cannot be empty."
            )

        if student_level not in self.DIFFICULTY_VALUE:
            raise ValueError(
                "student_level must be easy, medium, or hard."
            )

        ranked_resources = []

        for resource in resources:

            # ------------------------------------------
            # STAGE 1: TOPIC RELEVANCE
            # ------------------------------------------

            relevance = self._relevance_score(
                concept_name=concept_name,
                resource=resource,
            )

            # Hard relevance gate.
            #
            # Difficulty and popularity must not rescue
            # a resource that is unrelated to the
            # student's requested concept.
            if relevance < self.minimum_relevance:
                continue

            # ------------------------------------------
            # STAGE 2: PERSONALIZATION
            # ------------------------------------------

            difficulty_match = (
                self._difficulty_match_score(
                    student_level=student_level,
                    resource_difficulty=resource.difficulty,
                )
            )

            quality = self._quality_score(
                resource
            )

            final_score = (
                self.relevance_weight * relevance
                + self.difficulty_weight * difficulty_match
                + self.quality_weight * quality
            )

            final_score = self._clip(
                final_score
            )

            reason = self._build_reason(
                relevance=relevance,
                difficulty_match=difficulty_match,
                quality=quality,
                student_level=student_level,
            )

            ranked_resources.append(
                RankedLearningResource(
                    resource=resource,
                    relevance_score=relevance,
                    difficulty_match_score=difficulty_match,
                    quality_score=quality,
                    final_score=final_score,
                    reason=reason,
                )
            )

        ranked_resources.sort(
            key=lambda item: item.final_score,
            reverse=True,
        )

        return ranked_resources

    # ==================================================
    # TOP-K RECOMMENDATIONS
    # ==================================================

    def top_k(
        self,
        concept_name: str,
        student_level: str,
        resources: list[LearningResource],
        k: int = 3,
    ) -> list[RankedLearningResource]:
        """
        Return the strongest K personalized resources
        after relevance filtering and ranking.
        """

        if k <= 0:
            raise ValueError(
                "k must be greater than zero."
            )

        ranked = self.rank(
            concept_name=concept_name,
            student_level=student_level,
            resources=resources,
        )

        return ranked[:k]

    # ==================================================
    # RELEVANCE
    # ==================================================

    def _relevance_score(
        self,
        concept_name: str,
        resource: LearningResource,
    ) -> float:
        """
        Estimate transparent lexical topic relevance.

        Concept terms are compared with:
        - resource title
        - description
        - topic tags

        No LLM is used.
        """

        concept_terms = self._tokenize(
            concept_name
        )

        if not concept_terms:
            return 0.0

        title_terms = self._tokenize(
            resource.title
        )

        description_terms = self._tokenize(
            resource.description
        )

        topic_terms = set()

        for topic in resource.topics:
            topic_terms.update(
                self._tokenize(topic)
            )

        title_overlap = self._overlap(
            concept_terms,
            title_terms,
        )

        description_overlap = self._overlap(
            concept_terms,
            description_terms,
        )

        topic_overlap = self._overlap(
            concept_terms,
            topic_terms,
        )

        # Title is treated as the strongest lexical
        # relevance signal.
        score = (
            0.60 * title_overlap
            + 0.20 * description_overlap
            + 0.20 * topic_overlap
        )

        return self._clip(score)

    # ==================================================
    # DIFFICULTY MATCH
    # ==================================================

    def _difficulty_match_score(
        self,
        student_level: str,
        resource_difficulty: str,
    ) -> float:
        """
        Compare resource difficulty with the student's
        current learning level.

        Exact match       -> 1.00
        One level away    -> 0.60
        Two levels away   -> 0.20

        These values are current project heuristics.
        """

        student_value = self.DIFFICULTY_VALUE[
            student_level
        ]

        resource_value = self.DIFFICULTY_VALUE[
            resource_difficulty
        ]

        difference = abs(
            student_value - resource_value
        )

        if difference == 0:
            return 1.0

        if difference == 1:
            return 0.60

        return 0.20

    # ==================================================
    # QUALITY
    # ==================================================

    def _quality_score(
        self,
        resource: LearningResource,
    ) -> float:
        """
        Estimate resource quality from available metadata.

        Popularity is only one weak quality signal.

        Missing popularity information does not
        automatically make a resource low quality.
        """

        score = 0.50

        # ----------------------------------------------
        # Popularity signal
        # ----------------------------------------------

        if (
            resource.view_count is not None
            and resource.view_count >= 0
        ):

            # Log scaling prevents extremely popular
            # resources from dominating the score.
            popularity = (
                math.log10(resource.view_count + 1)
                / 7.0
            )

            popularity = self._clip(
                popularity
            )

            score = (
                0.50 * score
                + 0.50 * popularity
            )

        # ----------------------------------------------
        # Metadata completeness
        # ----------------------------------------------

        metadata_bonus = 0.0

        if resource.description.strip():
            metadata_bonus += 0.05

        if resource.topics:
            metadata_bonus += 0.05

        if resource.source.strip():
            metadata_bonus += 0.05

        score += metadata_bonus

        return self._clip(score)

    # ==================================================
    # EXPLAINABLE RECOMMENDATION
    # ==================================================

    @staticmethod
    def _build_reason(
        relevance: float,
        difficulty_match: float,
        quality: float,
        student_level: str,
    ) -> str:

        reasons = []

        if relevance >= 0.75:
            reasons.append(
                "strong topic relevance"
            )

        else:
            reasons.append(
                "acceptable topic relevance"
            )

        if difficulty_match >= 0.90:
            reasons.append(
                f"well matched to the student's "
                f"{student_level} learning level"
            )

        elif difficulty_match >= 0.50:
            reasons.append(
                "reasonably close to the student's "
                "current learning level"
            )

        else:
            reasons.append(
                "more challenging than the student's "
                "current learning level"
            )

        if quality >= 0.70:
            reasons.append(
                "strong available quality signals"
            )

        return (
            "Recommended based on "
            + ", ".join(reasons)
            + "."
        )

    # ==================================================
    # HELPERS
    # ==================================================

    @staticmethod
    def _tokenize(
        text: str,
    ) -> set[str]:

        return set(
            re.findall(
                r"[a-z0-9]+",
                text.lower(),
            )
        )

    @staticmethod
    def _overlap(
        concept_terms: set[str],
        candidate_terms: set[str],
    ) -> float:

        if not concept_terms:
            return 0.0

        matched = (
            concept_terms
            & candidate_terms
        )

        return (
            len(matched)
            / len(concept_terms)
        )

    @staticmethod
    def _clip(
        value: float,
    ) -> float:

        return max(
            0.0,
            min(1.0, value),
        )