from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from app.research_agent.models import ResearchPaper


class OpenAlexSearchError(RuntimeError):
    """
    Raised when OpenAlex paper retrieval fails.
    """


class OpenAlexSearch:
    """
    Retrieves scholarly works from OpenAlex and converts
    them into the common ResearchPaper representation used
    by our Research Agent.
    """

    BASE_URL = "https://api.openalex.org/works"

    def __init__(
        self,
        timeout: int = 20,
    ):
        self.timeout = timeout

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> list[ResearchPaper]:

        query = query.strip()

        if not query:
            raise ValueError("Search query cannot be empty")

        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")

        params = urllib.parse.urlencode(
            {
                "search": query,
                "per-page": limit,
            }
        )

        url = f"{self.BASE_URL}?{params}"

        request = urllib.request.Request(
            url=url,
            headers={
                "User-Agent": "CACM-PHSS-Research-Agent/1.0",
                "Accept": "application/json",
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
            ) as response:

                raw_data = response.read().decode("utf-8")

        except urllib.error.HTTPError as exc:
            raise OpenAlexSearchError(
                f"OpenAlex returned HTTP {exc.code}: "
                f"{exc.reason}"
            ) from exc

        except urllib.error.URLError as exc:
            raise OpenAlexSearchError(
                "Could not connect to OpenAlex: "
                f"{exc.reason}"
            ) from exc

        except TimeoutError as exc:
            raise OpenAlexSearchError(
                "OpenAlex request timed out"
            ) from exc

        try:
            payload = json.loads(raw_data)

        except json.JSONDecodeError as exc:
            raise OpenAlexSearchError(
                "OpenAlex returned invalid JSON"
            ) from exc

        return self._parse_papers(payload)

    def _parse_papers(
        self,
        payload: dict,
    ) -> list[ResearchPaper]:

        papers: list[ResearchPaper] = []

        for item in payload.get("results", []):

            title = (
                item.get("display_name")
                or item.get("title")
                or ""
            ).strip()

            if not title:
                continue

            authors: list[str] = []

            for authorship in item.get(
                "authorships",
                [],
            ):

                author = authorship.get(
                    "author",
                    {},
                )

                name = (
                    author.get("display_name")
                    or ""
                ).strip()

                if name:
                    authors.append(name)

            abstract = self._reconstruct_abstract(
                item.get("abstract_inverted_index")
            )

            openalex_id = (
                item.get("id") or ""
            ).strip()

            paper_id = ""

            if openalex_id:
                paper_id = (
                    openalex_id
                    .rstrip("/")
                    .split("/")[-1]
                )

            paper_url = self._get_best_url(item)

            papers.append(
                ResearchPaper(
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    url=paper_url,
                    year=item.get("publication_year"),
                    source="openalex",
                    paper_id=paper_id,
                )
            )

        return papers

    def _get_best_url(
        self,
        item: dict,
    ) -> str:

        primary_location = (
            item.get("primary_location")
            or {}
        )

        landing_page_url = (
            primary_location.get("landing_page_url")
            or ""
        ).strip()

        if landing_page_url:
            return landing_page_url

        return (
            item.get("id")
            or ""
        ).strip()

    def _reconstruct_abstract(
        self,
        inverted_index: dict | None,
    ) -> str:

        if not inverted_index:
            return ""

        positioned_words: list[
            tuple[int, str]
        ] = []

        for word, positions in inverted_index.items():

            for position in positions:

                positioned_words.append(
                    (position, word)
                )

        positioned_words.sort(
            key=lambda item: item[0]
        )

        return " ".join(
            word
            for _, word
            in positioned_words
        )