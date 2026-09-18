from app.cognitive.models import StudentCognitiveModel

from app.learning_agent.resources.models import (
    ResourceRecommendation,
)

from app.learning_agent.resources.resource_ranker import (
    LearningResourceRanker,
)

from app.learning_agent.resources.youtube_retriever import (
    YouTubeResourceRetriever,
)


class LearningResourceRecommender:
    """
    CACM-aware personalized learning resource recommender.

    Pipeline:

        Student Cognitive State
                |
                v
        Determine Target Level
                |
                v
        Difficulty-Aware Retrieval
                |
                v
        Independent Difficulty Estimation
                |
                v
        Relevance Filtering
                |
                v
        Personalized Ranking
                |
                v
        Top-K Recommendations

    The student does not manually choose easy, medium,
    or hard resources.

    The target level is derived from the student's
    current CACM cognitive state.

    Current thresholds and ranking rules are prototype
    heuristics and should later be experimentally
    evaluated and calibrated.
    """

    def __init__(
        self,
        retriever=None,
        ranker=None,
    ):
        self.retriever = (
            retriever
            if retriever is not None
            else YouTubeResourceRetriever()
        )

        self.ranker = (
            ranker
            if ranker is not None
            else LearningResourceRanker()
        )

    # ==================================================
    # PUBLIC METHOD
    # ==================================================

    def recommend(
        self,
        student: StudentCognitiveModel,
        concept_name: str,
        top_k: int = 3,
        candidate_count: int = 10,
    ) -> ResourceRecommendation:
        """
        Recommend personalized resources for one concept.

        The student's CACM state determines the desired
        resource difficulty.

        That target level influences BOTH:

        1. Which resources are retrieved.
        2. How retrieved resources are ranked.

        The actual difficulty assigned to each resource
        is still independently estimated from its
        metadata.
        """

        concept_name = concept_name.strip()

        if not concept_name:
            raise ValueError(
                "concept_name cannot be empty."
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        if candidate_count <= 0:
            raise ValueError(
                "candidate_count must be greater than zero."
            )

        # ----------------------------------------------
        # STEP 1: READ SHARED CACM STATE
        # ----------------------------------------------

        concept_state = student.get_concept(
            concept_name
        )

        # ----------------------------------------------
        # STEP 2: DETERMINE TARGET RESOURCE LEVEL
        # ----------------------------------------------

        student_level = self._determine_student_level(
            mastery=concept_state.mastery,
            confidence=concept_state.confidence,
            attempts=concept_state.attempts,
        )

        # ----------------------------------------------
        # STEP 3: DIFFICULTY-AWARE REAL RETRIEVAL
        # ----------------------------------------------
        #
        # CACM now affects retrieval itself.
        #
        # Example:
        #
        # weak student:
        #   recursion -> beginner/basic resources
        #
        # stronger student:
        #   recursion -> advanced/problem resources
        #
        # The retriever does NOT blindly label returned
        # resources with this level. Each candidate is
        # independently classified by the difficulty
        # estimator.
        # ----------------------------------------------

        resources = self.retriever.search(
            concept_name=concept_name,
            max_results=candidate_count,
            target_level=student_level,
        )

        # ----------------------------------------------
        # STEP 4: PERSONALIZED RESOURCE RANKING
        # ----------------------------------------------
        #
        # The ranker considers:
        #
        # - concept relevance
        # - difficulty match
        # - quality signals
        #
        # Resources with insufficient relevance are
        # filtered before final ranking.
        # ----------------------------------------------

        ranked_resources = self.ranker.top_k(
            concept_name=concept_name,
            student_level=student_level,
            resources=resources,
            k=top_k,
        )

        # ----------------------------------------------
        # STEP 5: RETURN EXPLAINABLE RECOMMENDATION
        # ----------------------------------------------

        return ResourceRecommendation(
            concept_name=concept_name,
            student_level=student_level,
            resources=ranked_resources,
        )

    # ==================================================
    # COGNITIVE LEVEL SELECTION
    # ==================================================

    @staticmethod
    def _determine_student_level(
        mastery: float,
        confidence: float,
        attempts: int,
    ) -> str:
        """
        Convert CACM cognitive state into a target
        resource difficulty.

        IMPORTANT:

        A student's initial neutral mastery prior must
        not be interpreted as demonstrated knowledge.

        Current prototype policy:

            attempts == 0
                -> easy

            mastery < 0.40
                -> easy

            mastery < 0.70
                -> medium

            mastery >= 0.70 but confidence < 0.50
                -> medium

            mastery >= 0.70 and confidence >= 0.50
                -> hard
        """

        # No observed evidence yet.
        if attempts == 0:
            return "easy"

        # Evidence suggests weak mastery.
        if mastery < 0.40:
            return "easy"

        # Developing mastery.
        if mastery < 0.70:
            return "medium"

        # High estimated mastery, but CACM is not yet
        # sufficiently confident in that estimate.
        if confidence < 0.50:
            return "medium"

        # High mastery supported by sufficient confidence.
        return "hard"