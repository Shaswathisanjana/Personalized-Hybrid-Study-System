import re


class ResourceDifficultyEstimator:
    """
    Estimate the educational difficulty of a resource
    using transparent lexical signals.

    This component does NOT use an LLM.

    The current rules are prototype heuristics and
    should later be evaluated against labelled resources.

    Output:
        easy
        medium
        hard
    """

    EASY_TERMS = {
        "beginner": 3,
        "beginners": 3,
        "basic": 3,
        "basics": 3,
        "introduction": 3,
        "intro": 2,
        "getting started": 3,
        "fundamentals": 2,
        "fundamental": 2,
        "simple": 2,
        "simply": 2,
        "explained": 1,
        "easy": 3,
        "first": 1,
        "learn": 1,
    }

    MEDIUM_TERMS = {
        "intermediate": 3,
        "examples": 2,
        "example": 1,
        "practice": 2,
        "exercise": 2,
        "exercises": 2,
        "implementation": 2,
        "implement": 2,
        "problems": 2,
        "problem solving": 2,
        "coding": 1,
        "tutorial": 1,
    }

    HARD_TERMS = {
        "advanced": 4,
        "optimization": 3,
        "optimisation": 3,
        "complexity": 3,
        "time complexity": 4,
        "space complexity": 4,
        "dynamic programming": 4,
        "competitive programming": 4,
        "deep dive": 3,
        "expert": 4,
        "challenging": 3,
        "hard": 3,
        "proof": 2,
        "analysis": 2,
    }

    def estimate(
        self,
        title: str,
        description: str = "",
    ) -> str:
        """
        Estimate resource difficulty from title and
        description.

        Title signals receive greater importance because
        educational video titles usually describe the
        intended audience or content level more directly.
        """

        title = self._normalize(title)
        description = self._normalize(description)

        easy_score = self._score_text(
            title,
            self.EASY_TERMS,
            multiplier=2,
        )

        easy_score += self._score_text(
            description,
            self.EASY_TERMS,
            multiplier=1,
        )

        medium_score = self._score_text(
            title,
            self.MEDIUM_TERMS,
            multiplier=2,
        )

        medium_score += self._score_text(
            description,
            self.MEDIUM_TERMS,
            multiplier=1,
        )

        hard_score = self._score_text(
            title,
            self.HARD_TERMS,
            multiplier=2,
        )

        hard_score += self._score_text(
            description,
            self.HARD_TERMS,
            multiplier=1,
        )

        return self._select_level(
            easy_score=easy_score,
            medium_score=medium_score,
            hard_score=hard_score,
        )

    # ==================================================
    # SCORING
    # ==================================================

    @staticmethod
    def _score_text(
        text: str,
        terms: dict[str, int],
        multiplier: int,
    ) -> int:

        score = 0

        for term, weight in terms.items():

            if ResourceDifficultyEstimator._contains_term(
                text,
                term,
            ):
                score += weight * multiplier

        return score

    # ==================================================
    # LEVEL DECISION
    # ==================================================

    @staticmethod
    def _select_level(
        easy_score: int,
        medium_score: int,
        hard_score: int,
    ) -> str:
        """
        Select the strongest detected level.

        Hard signals receive priority in a tie because
        recommending an advanced resource as beginner
        material is more harmful than conservatively
        marking it as difficult.

        If no useful difficulty signal is available,
        medium is used as a neutral fallback.
        """

        highest = max(
            easy_score,
            medium_score,
            hard_score,
        )

        if highest == 0:
            return "medium"

        if hard_score == highest:
            return "hard"

        if easy_score == highest:
            return "easy"

        return "medium"

    # ==================================================
    # TEXT HELPERS
    # ==================================================

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:

        text = text.lower()

        text = re.sub(
            r"[^a-z0-9+# ]+",
            " ",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    @staticmethod
    def _contains_term(
        text: str,
        term: str,
    ) -> bool:

        pattern = (
            r"\b"
            + re.escape(term)
            + r"\b"
        )

        return bool(
            re.search(pattern, text)
        )