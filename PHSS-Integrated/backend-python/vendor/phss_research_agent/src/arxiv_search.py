"""Topic-independent arXiv retrieval, review filtering, and semantic ranking."""
from __future__ import annotations

import os
import re
import json
import hashlib
from pathlib import Path
from functools import lru_cache
from typing import Any

import numpy as np
import arxiv
from .embeddings import BGEEmbedder

# Strong title signals for review-style publications. Patterns intentionally include
# common variants while avoiding a blanket ban on words like "review" in an abstract.
_SURVEY_TITLE_PATTERN = re.compile(
    r"\b(?:survey|systematic\s+review|literature\s+review|scoping\s+review|"
    r"comprehensive\s+review|state[- ]of[- ]the[- ]art\s+review|review\s+paper|"
    r"mapping\s+study|bibliometric(?:\s+analysis|\s+review)?|meta[- ]analysis|"
    r"systematic\s+mapping)\b", re.IGNORECASE)

_SURVEY_ABSTRACT_PATTERNS = (
    r"\bwe present (?:a|an) (?:comprehensive |systematic |critical )?(?:survey|review)\b",
    r"\bthis (?:paper|article|study) (?:presents|provides|offers) (?:a|an) (?:comprehensive |systematic |critical )?(?:survey|review)\b",
    r"\b(?:systematically|comprehensively) review(?:s|ed|ing)? the literature\b",
    r"\bwe conduct (?:a|an) (?:systematic )?(?:literature )?review\b",
    r"\bthis survey aims to\b",
    r"\ba survey of (?:recent|existing|current|the)\b",
    r"\bthis review (?:summarizes|reviews|surveys|synthesizes|analyzes)\b",
    r"\bwe review existing (?:methods|approaches|techniques|literature|work)\b",
    r"\b(systematic literature review|literature survey|review of the state of the art)\b",
    r"\b(meta[- ]analysis|bibliometric analysis)\b",
)


def is_survey_paper(title: str, abstract: str) -> bool:
    """Return True for likely surveys/reviews based on title and abstract signals."""
    title = re.sub(r"\s+", " ", title or "").strip()
    abstract = re.sub(r"\s+", " ", abstract or "").strip()
    if _SURVEY_TITLE_PATTERN.search(title):
        return True
    # Check the full abstract, not only its opening 140 words; review-type declaration
    # often appears in the final sentences of an abstract.
    return any(re.search(pattern, abstract, re.IGNORECASE) for pattern in _SURVEY_ABSTRACT_PATTERNS)


@lru_cache(maxsize=1)
def get_cached_embedder() -> BGEEmbedder:
    """Load one BGE embedder instance and reuse it for ranking and gap analysis."""
    return BGEEmbedder()


def _as_2d_array(values: Any) -> np.ndarray:
    array = np.asarray(values, dtype=np.float32)
    return array.reshape(1, -1) if array.ndim == 1 else array


def _cosine_scores(query_embedding: Any, document_embeddings: Any) -> np.ndarray:
    query = _as_2d_array(query_embedding)[0]
    documents = _as_2d_array(document_embeddings)
    denominator = np.linalg.norm(documents, axis=1) * np.linalg.norm(query)
    denominator[denominator == 0] = 1e-12
    return np.dot(documents, query) / denominator


def _make_record(result: Any) -> dict:
    """Convert arXiv Result metadata into the dict format expected downstream."""
    return {
        "title": (getattr(result, "title", None) or "").strip(),
        "abstract": (getattr(result, "summary", None) or "").strip(),
        "authors": [author.name for author in (getattr(result, "authors", []) or [])],
        "published": result.published.isoformat() if getattr(result, "published", None) else None,
        "updated": result.updated.isoformat() if getattr(result, "updated", None) else None,
        "url": getattr(result, "entry_id", "") or "",
        "pdf_url": getattr(result, "pdf_url", None),
    }


def clean_research_topic(topic: str) -> str:
    """Strip conversational commands and fluff to isolate academic keywords."""
    text = (topic or "").strip()
    patterns = [
        r"^(?:(?:can|could|would)\s+you\s+)?(?:please\s+)?(?:give|show|provide|get|find|fetch|search|generate|write|create|prepare|make)\s+(?:me\s+)?(?:a\s+)?(?:detailed\s+|comprehensive\s+|full\s+|brief\s+)?(?:research\s+)?(?:report|literature\s+review|review|paper|papers|study|studies|summary|overview)\s+(?:on|about|for|regarding|involving)\s+",
        r"^(?:(?:can|could|would)\s+you\s+)?(?:please\s+)?(?:tell|inform)\s+(?:me\s+)?about\s+",
        r"^(?:i\s+want\s+to\s+learn|i\s+need\s+a\s+report|i\s+need\s+papers)\s+(?:on|about|for)\s+",
        r"^(?:what\s+are\s+the\s+latest\s+papers\s+on)\s+",
        r"^(?:research\s+paper\s+on|research\s+on|papers\s+on|literature\s+review\s+on)\s+",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"(?:,\s*please|\s+please|\s+thanks|\s+thank\s+you)[.?!]*$", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"[,.?!;:]+$", "", text).strip()
    return text if len(text) >= 2 else (topic or "").strip()


def search_arxiv(topic: str, max_results: int = 5):
    """Retrieve and rank likely original-research papers; never intentionally fill with reviews.

    Environment variables:
      ARXIV_CANDIDATE_LIMIT: candidates inspected (default scales to requested count)
      ARXIV_MIN_RELEVANCE: minimum BGE cosine similarity (default 0.30)
    """
    topic = clean_research_topic(topic)
    if not topic:
        raise ValueError("Research topic cannot be empty.")
    max_results = max(1, min(int(max_results), 10))
    default_candidate_limit = min(max(max_results * 8, 40), 80)
    candidate_limit = int(os.getenv("ARXIV_CANDIDATE_LIMIT", default_candidate_limit))
    candidate_limit = max(max_results, min(candidate_limit, 100))
    min_relevance = float(os.getenv("ARXIV_MIN_RELEVANCE", "0.30"))

    # Persistent cache avoids calling arXiv again for a topic already searched successfully.
    cache_dir = Path(os.getenv("PHSS_SEARCH_CACHE_DIR", "outputs/search_cache"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(f"{topic.lower()}|{candidate_limit}|{max_results}".encode("utf-8")).hexdigest()[:20]
    cache_path = cache_dir / f"arxiv_{cache_key}.json"
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(cached, list) and cached:
                print(f"  Using {len(cached)} cached arXiv results for this topic.")
                return cached
        except (OSError, json.JSONDecodeError):
            pass

    # Keep the client from performing rapid internal retries during a rate limit.
    # page_size matches candidate_limit to fetch in a single HTTP request without multi-page delay penalties.
    client = arxiv.Client(page_size=min(candidate_limit, 25), delay_seconds=3.0, num_retries=0)
    search = arxiv.Search(query=topic, max_results=candidate_limit,
                          sort_by=arxiv.SortCriterion.Relevance)
    records, seen_ids = [], set()
    print(f"  Retrieving up to {candidate_limit} candidates before filtering...")
    skipped_reviews = 0
    try:
        for result in client.results(search):
            record = _make_record(result)
            paper_id = record["url"] or record["title"]
            if paper_id in seen_ids:
                continue
            seen_ids.add(paper_id)
            if not record["title"] or not record["abstract"]:
                continue
            if is_survey_paper(record["title"], record["abstract"]):
                skipped_reviews += 1
                print(f"  Skipping likely survey/review: {record['title']}")
                continue
            record["paper_type"] = "original_research_candidate"
            records.append(record)
    except arxiv.HTTPError as exc:
        status = getattr(exc, "status", None) or getattr(exc, "status_code", None)
        if status in (429, 503) or "429" in str(exc) or "503" in str(exc):
            raise RuntimeError(
                "arXiv is temporarily rate-limiting or unavailable (HTTP 429/503). "
                "No rapid retries were made. Wait before trying again. If this topic was "
                "searched successfully before, the saved cache will be reused automatically."
            ) from exc
        raise RuntimeError(f"arXiv search failed: {exc}") from exc

    print(f"  Filtered {skipped_reviews} likely survey/review paper(s).")
    if not records:
        print("  No non-review candidates with abstracts were found.")
        return []

    embedder = get_cached_embedder()
    topic_embedding = embedder.embed_query(topic)
    document_texts = [f"Title: {p['title']}\nAbstract: {p['abstract']}" for p in records]
    document_embeddings = embedder.embed_documents(document_texts)
    scores = _cosine_scores(topic_embedding, document_embeddings)
    for paper, score in zip(records, scores):
        paper["relevance_score"] = round(float(score), 4)
        paper["relevance_method"] = "BGE cosine similarity of topic vs title and abstract"
    records.sort(key=lambda p: p["relevance_score"], reverse=True)
    selected = [p for p in records if p["relevance_score"] >= min_relevance][:max_results]
    if len(selected) < max_results:
        print(f"  Warning: only {len(selected)} of {max_results} requested papers passed review filtering and relevance threshold ({min_relevance:.2f}).")
    for paper in selected:
        print(f"  Relevance score: {paper['relevance_score']:.3f} | {paper['title']}")
    if selected:
        try:
            cache_path.write_text(json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            print(f"  Warning: could not save search cache: {exc}")
    return selected
