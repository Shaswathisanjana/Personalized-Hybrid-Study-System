from __future__ import annotations

import re
from dataclasses import dataclass

from app.research_agent.models import ResearchPaper


@dataclass
class RankedPaper:
    """
    A research paper together with its relevance score.

    The score is not a scientific quality score.
    It represents estimated textual relevance to the
    student's current research query.
    """

    paper: ResearchPaper
    relevance_score: float
    matched_terms: list[str]


class PaperRelevanceRanker:
    """
    Deterministic and explainable first-stage paper ranker.

    Current policy:
        - Query terms appearing in the TITLE receive
          stronger weight.
        - Query terms appearing in the ABSTRACT receive
          additional weight.
        - Papers are ranked from highest to lowest score.

    This is intentionally separate from OpenAlex ranking.
    """

    STOP_WORDS = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "what",
        "when",
        "where",
        "which",
        "why",
        "with",
    }

    def __init__(
        self,
        title_weight: float = 0.70,
        abstract_weight: float = 0.30,
    ):
        if title_weight < 0:
            raise ValueError(
                "title_weight cannot be negative"
            )

        if abstract_weight < 0:
            raise ValueError(
                "abstract_weight cannot be negative"
            )

        total = title_weight + abstract_weight

        if total <= 0:
            raise ValueError(
                "At least one relevance weight "
                "must be positive"
            )

        self.title_weight = title_weight / total
        self.abstract_weight = abstract_weight / total

    def rank(
        self,
        query: str,
        papers: list[ResearchPaper],
    ) -> list[RankedPaper]:
        """
        Rank papers according to textual relevance.
        """

        query_terms = self._extract_terms(query)

        if not query_terms:
            raise ValueError(
                "Query does not contain usable terms"
            )

        ranked: list[RankedPaper] = []

        for paper in papers:

            ranked.append(
                self._score_paper(
                    query_terms=query_terms,
                    paper=paper,
                )
            )

        ranked.sort(
            key=lambda item: item.relevance_score,
            reverse=True,
        )

        return ranked

    def top_k(
        self,
        query: str,
        papers: list[ResearchPaper],
        k: int = 3,
        minimum_score: float = 0.0,
    ) -> list[RankedPaper]:
        """
        Return the highest-ranked papers that meet
        the minimum relevance threshold.
        """

        if k <= 0:
            raise ValueError(
                "k must be greater than zero"
            )

        if not 0.0 <= minimum_score <= 1.0:
            raise ValueError(
                "minimum_score must be between 0 and 1"
            )

        ranked = self.rank(
            query=query,
            papers=papers,
        )

        filtered = [
            item
            for item in ranked
            if item.relevance_score >= minimum_score
        ]

        return filtered[:k]

    def _score_paper(
        self,
        query_terms: set[str],
        paper: ResearchPaper,
    ) -> RankedPaper:

        title_terms = self._extract_terms(
            paper.title
        )

        abstract_terms = self._extract_terms(
            paper.abstract
        )

        title_matches = (
            query_terms & title_terms
        )

        abstract_matches = (
            query_terms & abstract_terms
        )

        title_ratio = (
            len(title_matches)
            / len(query_terms)
        )

        abstract_ratio = (
            len(abstract_matches)
            / len(query_terms)
        )

        score = (
            self.title_weight * title_ratio
            + self.abstract_weight * abstract_ratio
        )

        matched_terms = sorted(
            title_matches | abstract_matches
        )

        return RankedPaper(
            paper=paper,
            relevance_score=round(score, 3),
            matched_terms=matched_terms,
        )

    def _extract_terms(
        self,
        text: str,
    ) -> set[str]:
        """
        Convert text into normalized content terms.
        """

        words = re.findall(
            r"[a-zA-Z0-9]+",
            text.lower(),
        )

        return {
            word
            for word in words
            if (
                len(word) > 1
                and word not in self.STOP_WORDS
            )
        }