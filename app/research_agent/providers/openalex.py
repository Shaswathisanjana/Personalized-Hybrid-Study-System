from __future__ import annotations

import json
import os
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

    def search_page(self, query, limit=20, cursor='*'):
        if not isinstance(query, str) or not query.strip() or not 1 <= limit <= 100:
            raise ValueError('Enter a topic and a page size between 1 and 100.')
        params = urllib.parse.urlencode({'search': query.strip(), 'per_page': limit, 'cursor': cursor})
        headers = {'User-Agent': 'CACM-PHSS-Research-Agent/1.0', 'Accept': 'application/json'}
        key = self.api_key or os.getenv('OPENALEX_API_KEY')
        if key:
            headers['Authorization'] = 'Bearer ' + key
        request = urllib.request.Request(self.BASE_URL + '?' + params, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read(8 * 1024 * 1024 + 1)
            if len(raw) > 8 * 1024 * 1024:
                raise OpenAlexSearchError('Academic response exceeds the 8 MiB page limit.')
            payload = json.loads(raw.decode('utf-8'))
            if not isinstance(payload, dict) or not isinstance(payload.get('results'), list):
                raise ValueError('Invalid result list')
            papers = self._parse_papers(payload)
            metadata = payload.get('meta') or {}
            return dict(papers=papers, next_cursor=metadata.get('next_cursor'),
                        total_count=metadata.get('count'),
                        raw_count=len(payload['results']),
                        warnings=[f"{len(payload['results']) - len(papers)} records without usable titles were skipped."]
                        if len(papers) != len(payload['results']) else [])
        except OpenAlexSearchError:
            raise
        except urllib.error.HTTPError as exc:
            raise OpenAlexSearchError(f'OpenAlex HTTP {exc.code}: {exc.reason}; check provider credentials or quota.') from exc
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            raise OpenAlexSearchError(f'Academic page retrieval failed: {type(exc).__name__}') from exc

    def __init__(
        self,
        timeout: int = 20,
        api_key: str | None = None,
    ):
        self.timeout = timeout
        self.api_key = api_key

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
        key = self.api_key or os.getenv('OPENALEX_API_KEY')
        if key:
            request.add_header('Authorization', 'Bearer ' + key)

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

            if not isinstance(item, dict):
                continue

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
            ) or []:

                if not isinstance(authorship, dict):
                    continue

                author = authorship.get(
                    "author",
                    {},
                ) or {}

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
                    doi=item.get('doi') or '',
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
