
import os
import re
import time
import math
import logging

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
logger = logging.getLogger(__name__)

FIELDS = (
    "title,abstract,year,authors,url,venue,"
    "citationCount,openAccessPdf,externalIds"
)

# Strong review indicators. Avoid filtering every paper that merely
# contains words such as "analysis" or "survey" in its abstract.
REVIEW_TITLE_PATTERNS = [
    r"\b(systematic|comprehensive|literature|scoping)\s+review\b",
    r"\breview\s+(of|on|for)\b",
    r"\bstate[- ]of[- ]the[- ]art\s+review\b",
    r"\bsurvey\s+(of|on)\b",
    r"\bmapping\s+study\b",
    r"\bmeta[- ]analysis\b",
]


def is_review_paper(title: str, abstract: str = "") -> bool:
    """Identify likely review/survey papers from their titles."""
    title = (title or "").lower().strip()

    return any(
        re.search(pattern, title)
        for pattern in REVIEW_TITLE_PATTERNS
    )


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (title or "").lower())


def _topic_terms(topic: str) -> set[str]:
    stopwords = {
        "the", "and", "for", "with", "from", "using", "based",
        "into", "via", "of", "in", "on", "to", "a", "an",
        "by", "deep", "learning", "research", "study",
    }
    return {
        term for term in re.findall(r"[a-z0-9]+", topic.lower())
        if term not in stopwords and len(term) > 2
    }


def _rank_score(paper: dict, topic: str) -> float:
    """Heuristic candidate ranking, not a scientific quality score."""
    title = (paper.get("title") or "").lower()
    abstract = (paper.get("abstract") or "").lower()
    terms = _topic_terms(topic)

    if not terms:
        relevance = 0.0
    else:
        title_matches = sum(term in title for term in terms)
        text_matches = sum(term in (title + " " + abstract) for term in terms)
        relevance = (
            0.65 * title_matches / len(terms)
            + 0.35 * text_matches / len(terms)
        )

    year = paper.get("year")
    current_year = time.gmtime().tm_year
    recency = (
        max(0.0, min(1.0, (year - (current_year - 10)) / 10))
        if isinstance(year, int)
        else 0.0
    )

    citations = paper.get("citation_count") or 0
    citation_score = min(1.0, math.log1p(max(0, citations)) / math.log1p(500))

    # Relevance dominates. Recency helps discover recent methods.
    # Citations have limited influence so recent papers are not suppressed.
    return 0.70 * relevance + 0.25 * recency + 0.05 * citation_score


def search_semantic_scholar(
    topic: str,
    limit: int = 50,
    exclude_reviews: bool = True,
) -> list[dict]:
    """Retrieve, normalize, deduplicate and rank Semantic Scholar results."""
    if not topic or not topic.strip():
        return []

    limit = max(1, min(int(limit), 100))
    api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    headers = {"x-api-key": api_key} if api_key else {}

    params = {
        "query": topic.strip(),
        "limit": limit,
        "fields": FIELDS,
    }

    for attempt in range(3):
        try:
            response = requests.get(
                API_URL,
                params=params,
                headers=headers,
                timeout=30,
            )

            if response.status_code == 429:
                if attempt == 2:
                    logger.warning("Semantic Scholar rate limit reached.")
                    return []
                retry_after = response.headers.get("Retry-After", "")
                delay = (
                    min(int(retry_after), 60)
                    if retry_after.isdigit()
                    else 5 * (attempt + 1)
                )
                time.sleep(delay)
                continue

            if response.status_code >= 500 and attempt < 2:
                time.sleep(3 * (attempt + 1))
                continue

            response.raise_for_status()
            raw_papers = response.json().get("data", [])
            papers = []
            seen = set()

            for item in raw_papers:
                title = (item.get("title") or "").strip()
                if not title:
                    continue

                external_ids = item.get("externalIds") or {}
                doi = (external_ids.get("DOI") or "").lower().strip()
                arxiv_id = (
                    external_ids.get("ArXiv")
                    or external_ids.get("ArXivID")
                    or ""
                ).lower().strip()

                key = doi or arxiv_id or _normalize_title(title)
                if key in seen:
                    continue
                seen.add(key)

                if exclude_reviews and is_review_paper(
                    title, item.get("abstract") or ""
                ):
                    continue

                paper = {
                    "title": title,
                    "abstract": item.get("abstract") or "",
                    "year": item.get("year"),
                    "authors": [
                        author.get("name", "")
                        for author in item.get("authors", [])
                    ],
                    "url": item.get("url") or "",
                    "venue": item.get("venue") or "",
                    "citation_count": item.get("citationCount"),
                    "pdf_url": (
                        (item.get("openAccessPdf") or {}).get("url")
                        or (f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else None)
                        or (item.get("url").replace("/abs/", "/pdf/") + ".pdf" if item.get("url") and "arxiv.org/abs/" in item.get("url") else None)
                    ),
                    "external_ids": external_ids,
                    "source": "Semantic Scholar",
                }

                paper["retrieval_score"] = _rank_score(paper, topic)
                papers.append(paper)

            papers.sort(
                key=lambda p: p["retrieval_score"],
                reverse=True,
            )
            return papers

        except requests.RequestException as exc:
            if attempt == 2:
                logger.warning("Semantic Scholar search failed: %s", exc)
                return []
            time.sleep(2 * (attempt + 1))

    return []
