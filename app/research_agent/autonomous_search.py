from __future__ import annotations

from dataclasses import dataclass, field

from app.research_agent.models import ResearchPaper
from app.research_agent.paper_search import AcademicPaperSearch
from app.research_agent.abstract_quality_validator import (
    AbstractQualityValidator,
)


@dataclass
class SearchAttempt:
    query: str
    retrieved_count: int
    usable_count: int
    reason: str


@dataclass
class RefinedSearchResult:
    papers: list[ResearchPaper] = field(default_factory=list)
    attempts: list[SearchAttempt] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    target_usable_papers: int = 0
    target_reached: bool = False


class AutonomousResearchSearcher:
    """
    Searches using a planned sequence of queries.

    After each attempt, evaluates abstract usability and
    decides whether another search is necessary.

    This module does not summarize papers or update CACM.
    """

    def __init__(
        self,
        search_service=None,
        validator=None,
        max_attempts: int = 3,
    ):

        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")

        self.search_service = (
            search_service
            if search_service is not None
            else AcademicPaperSearch()
        )

        self.validator = (
            validator
            if validator is not None
            else AbstractQualityValidator()
        )

        self.max_attempts = max_attempts

    @staticmethod
    def _paper_key(paper: ResearchPaper) -> str:

        if paper.paper_id:
            return paper.paper_id.strip().lower()

        if paper.url:
            return paper.url.strip().lower()

        return paper.title.strip().lower()

    def search(
        self,
        queries: list[str],
        limit: int = 5,
        target_usable_papers: int = 2,
    ) -> RefinedSearchResult:

        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100.")

        if target_usable_papers < 1:
            raise ValueError(
                "target_usable_papers must be at least 1."
            )

        cleaned_queries = []

        for query in queries:
            query = query.strip()

            if query and query not in cleaned_queries:
                cleaned_queries.append(query)

        if not cleaned_queries:
            raise ValueError("At least one search query is required.")

        result = RefinedSearchResult(
            target_usable_papers=target_usable_papers
        )

        seen = set()
        usable_count = 0

        for query in cleaned_queries[:self.max_attempts]:

            try:

                response = self.search_service.search(
                    query=query,
                    limit=limit,
                )

            except Exception as exc:

                result.warnings.append(
                    f"Search failed for '{query}': "
                    f"{type(exc).__name__}: {exc}"
                )

                result.attempts.append(
                    SearchAttempt(
                        query=query,
                        retrieved_count=0,
                        usable_count=usable_count,
                        reason="Search provider failed; trying next query.",
                    )
                )

                continue

            result.warnings.extend(
                getattr(response, "provider_errors", [])
            )

            retrieved_count = len(response.papers)

            for paper in response.papers:

                key = self._paper_key(paper)

                if key in seen:
                    continue

                seen.add(key)
                result.papers.append(paper)

                quality = self.validator.validate(
                    abstract=paper.abstract,
                    title=paper.title,
                )

                if quality.is_usable:
                    usable_count += 1

            if usable_count >= target_usable_papers:

                result.target_reached = True

                result.attempts.append(
                    SearchAttempt(
                        query=query,
                        retrieved_count=retrieved_count,
                        usable_count=usable_count,
                        reason=(
                            "Enough usable papers found. "
                            "No further search required."
                        ),
                    )
                )

                break

            result.attempts.append(
                SearchAttempt(
                    query=query,
                    retrieved_count=retrieved_count,
                    usable_count=usable_count,
                    reason=(
                        "Insufficient usable papers. "
                        "Refining search if another query is available."
                    ),
                )
            )

        if not result.target_reached:

            result.warnings.append(
                "The search ended without reaching the target "
                "number of usable papers."
            )

        return result
