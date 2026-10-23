from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

from dotenv import load_dotenv
from google import genai

from app.research_agent.models import ResearchPaper
from app.research_agent.relevance_ranker import (
    PaperRelevanceRanker,
    RankedPaper,
)


@dataclass
class SemanticRankedPaper:
    """
    Final hybrid relevance information for a retrieved paper.
    """

    paper: ResearchPaper
    lexical_score: float
    semantic_score: float
    combined_score: float
    reason: str


class SemanticPaperRanker:
    """
    Hybrid academic-paper relevance ranker.

    Pipeline:

        Retrieved papers
              ↓
        Lexical ranking
              ↓
        Diversified candidate selection
              ↓
        Gemini semantic evaluation
              ↓
        Final hybrid ranking

    Gemini never retrieves or invents papers.
    It only evaluates papers supplied by the
    academic retrieval layer.
    """

    def __init__(
        self,
        model_name: str = "gemini-3.1-flash-lite-preview",
        lexical_weight: float = 0.35,
        semantic_weight: float = 0.65,
    ):
        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY was not found in .env"
            )

        if lexical_weight < 0 or semantic_weight < 0:
            raise ValueError(
                "Ranking weights cannot be negative"
            )

        total_weight = (
            lexical_weight + semantic_weight
        )

        if total_weight <= 0:
            raise ValueError(
                "At least one ranking weight "
                "must be positive"
            )

        self.lexical_weight = (
            lexical_weight / total_weight
        )

        self.semantic_weight = (
            semantic_weight / total_weight
        )

        self.model_name = model_name

        self.client = genai.Client(
            api_key=api_key
        )

        self.lexical_ranker = (
            PaperRelevanceRanker()
        )

    def rank(
        self,
        query: str,
        papers: list[ResearchPaper],
        candidate_limit: int = 5,
    ) -> list[SemanticRankedPaper]:

        query = query.strip()

        if not query:
            raise ValueError(
                "Research query cannot be empty"
            )

        if not papers:
            return []

        if candidate_limit <= 0:
            raise ValueError(
                "candidate_limit must be greater than zero"
            )

        # ==================================================
        # STAGE 1 — LEXICAL RANKING
        # ==================================================

        lexical_results = (
            self.lexical_ranker.rank(
                query=query,
                papers=papers,
            )
        )

        # ==================================================
        # STAGE 2 — DIVERSIFIED CANDIDATE SELECTION
        # ==================================================

        candidates = self._select_candidates(
            query=query,
            lexical_results=lexical_results,
            candidate_limit=candidate_limit,
        )

        # ==================================================
        # STAGE 3 — SEMANTIC EVALUATION
        # ==================================================

        semantic_results: list[
            SemanticRankedPaper
        ] = []

        for candidate in candidates:

            semantic_score, reason = (
                self._semantic_score(
                    query=query,
                    ranked_paper=candidate,
                )
            )

            combined_score = (
                self.lexical_weight
                * candidate.relevance_score
                + self.semantic_weight
                * semantic_score
            )

            semantic_results.append(
                SemanticRankedPaper(
                    paper=candidate.paper,
                    lexical_score=(
                        candidate.relevance_score
                    ),
                    semantic_score=(
                        semantic_score
                    ),
                    combined_score=round(
                        combined_score,
                        3,
                    ),
                    reason=reason,
                )
            )

        semantic_results.sort(
            key=lambda result:
            result.combined_score,
            reverse=True,
        )

        return semantic_results

    def _select_candidates(
        self,
        query: str,
        lexical_results: list[RankedPaper],
        candidate_limit: int,
    ) -> list[RankedPaper]:
        """
        Select candidates using two signals:

        1. Overall lexical relevance.
        2. Strong occurrence of the core query concept.

        This prevents a paper focused on the main topic
        from being discarded simply because generic
        contextual words dominate the lexical score.
        """

        if not lexical_results:
            return []

        # --------------------------------------------------
        # Extract meaningful query terms.
        # --------------------------------------------------

        query_terms = self._extract_query_terms(
            query
        )

        if not query_terms:
            return lexical_results[
                :candidate_limit
            ]

        # --------------------------------------------------
        # First query term is currently treated as the
        # primary/core concept.
        #
        # Example:
        # "recursion computer science education"
        #       ↓
        # core concept = "recursion"
        #
        # This is an explicit heuristic and can later be
        # replaced by structured query understanding.
        # --------------------------------------------------

        core_term = query_terms[0]

        selected: list[RankedPaper] = []

        selected_ids: set[str] = set()

        # --------------------------------------------------
        # Reserve most slots for strongest overall
        # lexical results.
        # --------------------------------------------------

        general_slots = max(
            1,
            candidate_limit - 1,
        )

        for ranked in lexical_results[
            :general_slots
        ]:

            selected.append(ranked)

            selected_ids.add(
                self._paper_identity(
                    ranked.paper
                )
            )

        # --------------------------------------------------
        # Find strongest paper containing the core term.
        # Search across ALL retrieved candidates,
        # not merely the lexical top few.
        # --------------------------------------------------

        core_candidates = []

        for ranked in lexical_results:

            searchable_text = (
                f"{ranked.paper.title} "
                f"{ranked.paper.abstract}"
            ).lower()

            if self._contains_term(
                searchable_text,
                core_term,
            ):
                core_candidates.append(
                    ranked
                )

        # Prefer title occurrence of core term.
        core_candidates.sort(
            key=lambda ranked: (
                self._contains_term(
                    ranked.paper.title.lower(),
                    core_term,
                ),
                ranked.relevance_score,
            ),
            reverse=True,
        )

        for ranked in core_candidates:

            identity = self._paper_identity(
                ranked.paper
            )

            if identity not in selected_ids:

                selected.append(ranked)

                selected_ids.add(identity)

                break

        # --------------------------------------------------
        # If diversification did not fill the requested
        # number of slots, fill remaining slots using
        # normal lexical ranking.
        # --------------------------------------------------

        for ranked in lexical_results:

            if len(selected) >= candidate_limit:
                break

            identity = self._paper_identity(
                ranked.paper
            )

            if identity in selected_ids:
                continue

            selected.append(ranked)

            selected_ids.add(identity)

        return selected[
            :candidate_limit
        ]

    def _semantic_score(
        self,
        query: str,
        ranked_paper: RankedPaper,
    ) -> tuple[float, str]:

        paper = ranked_paper.paper

        abstract = (
            paper.abstract.strip()
            if paper.abstract
            else "Not available"
        )

        prompt = f"""
You are evaluating the relevance of an already-retrieved
academic paper.

Research query:
{query}

Paper title:
{paper.title}

Paper abstract:
{abstract}

Judge ONLY how relevant this paper is to the research
query.

Important rules:

1. Do not invent information about the paper.
2. Use only the supplied title and abstract.
3. A paper directly focused on the main concept should
   score higher than a broad paper that merely contains
   contextual words.
4. General field overlap alone is not enough for a high
   score.

Give a relevance score from 0.0 to 1.0.

Interpretation:

0.0 = unrelated
0.25 = weakly related
0.50 = moderately related
0.75 = strongly related
1.0 = directly focused on the query

Return ONLY valid JSON:

{{
  "score": 0.0,
  "reason": "short explanation"
}}
"""

        try:

            response = (
                self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
            )

            text = response.text

            if not text:
                raise ValueError(
                    "Gemini returned an empty response"
                )

            cleaned = (
                self._clean_json_response(
                    text
                )
            )

            data = json.loads(
                cleaned
            )

            score = float(
                data["score"]
            )

            reason = str(
                data["reason"]
            ).strip()

            score = max(
                0.0,
                min(
                    1.0,
                    score,
                ),
            )

            if not reason:
                reason = (
                    "No semantic explanation provided."
                )

            return (
                round(score, 3),
                reason,
            )

        except Exception as exc:

            return (
                ranked_paper.relevance_score,
                (
                    "Semantic evaluation unavailable; "
                    "used lexical relevance as fallback. "
                    f"Reason: {type(exc).__name__}"
                ),
            )

    @staticmethod
    def _extract_query_terms(
        query: str,
    ) -> list[str]:

        stop_words = {
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

        words = re.findall(
            r"[a-zA-Z0-9]+",
            query.lower(),
        )

        return [
            word
            for word in words
            if (
                len(word) > 1
                and word not in stop_words
            )
        ]

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

        return (
            re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
            is not None
        )

    @staticmethod
    def _paper_identity(
        paper: ResearchPaper,
    ) -> str:

        if paper.paper_id:
            return paper.paper_id

        if paper.url:
            return paper.url

        return paper.title.lower().strip()

    @staticmethod
    def _clean_json_response(
        text: str,
    ) -> str:

        cleaned = text.strip()

        if cleaned.startswith("```"):

            lines = cleaned.splitlines()

            if lines:
                lines = lines[1:]

            if (
                lines
                and lines[-1]
                .strip()
                .startswith("```")
            ):
                lines = lines[:-1]

            cleaned = (
                "\n".join(lines).strip()
            )

        return cleaned