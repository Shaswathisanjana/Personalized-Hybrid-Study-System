from __future__ import annotations

from dataclasses import dataclass, field

from app.research_agent.models import ResearchPaper
from app.research_agent.providers.openalex import (
    OpenAlexSearch,
    OpenAlexSearchError,
)


class PaperSearchError(RuntimeError):
    """
    Raised when the Research Agent cannot retrieve
    academic papers from its configured providers.
    """


@dataclass
class PaperSearchResult:
    """
    Result returned by the Research Agent's academic
    search layer.

    We preserve provider failures instead of silently
    hiding them. This will later help with logging,
    debugging, and evaluation.
    """

    query: str

    papers: list[ResearchPaper] = field(
        default_factory=list
    )

    provider_used: str = ""

    provider_errors: list[str] = field(
        default_factory=list
    )


class AcademicPaperSearch:
    """
    Provider-independent academic paper search service.

    OpenAlex is currently the primary working provider.

    Additional providers can be plugged into this layer
    later without changing the Research Agent itself.
    """

    def __init__(
        self,
        openalex: OpenAlexSearch | None = None,
    ):

        self.openalex = (
            openalex
            if openalex is not None
            else OpenAlexSearch()
        )

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> PaperSearchResult:

        query = query.strip()

        if not query:
            raise ValueError(
                "Search query cannot be empty"
            )

        if not 1 <= limit <= 100:
            raise ValueError(
                "limit must be between 1 and 100"
            )

        provider_errors: list[str] = []

        # ==================================================
        # OPENALEX
        # ==================================================

        try:

            papers = self.openalex.search(
                query=query,
                limit=limit,
            )

            if papers:

                return PaperSearchResult(
                    query=query,
                    papers=papers,
                    provider_used="openalex",
                    provider_errors=provider_errors,
                )

            provider_errors.append(
                "OpenAlex returned no papers."
            )

        except OpenAlexSearchError as exc:

            provider_errors.append(
                str(exc)
            )

        # ==================================================
        # NO PROVIDER SUCCEEDED
        # ==================================================

        raise PaperSearchError(
            "Academic paper search failed. "
            + " | ".join(provider_errors)
        )