"""Bounded agentic control layer for the PHSS Research Agent.

This module adds a small plan -> retrieve -> evaluate -> adapt loop around the
existing PHSS pipeline. It intentionally limits extra searches to one so that
an arXiv rate limit or weak retrieval cannot cause an unbounded loop.
"""

from __future__ import annotations

import re
from typing import Callable


STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "by", "for", "from", "in",
    "into", "is", "of", "on", "or", "the", "to", "using", "with",
    "based", "approach", "detection", "deep", "learning", "research",
}


class AgenticResearchController:
    """Create a lightweight plan and select bounded next actions from evidence."""

    def __init__(
        self,
        max_adaptive_searches: int = 1,
        min_topic_overlap: float = 0.20,
        min_relevance_score: float = 0.30,
        min_relevant_ratio: float = 0.60,
    ):
        self.max_adaptive_searches = max(0, int(max_adaptive_searches))
        self.min_topic_overlap = max(0.0, min(1.0, float(min_topic_overlap)))
        self.min_relevance_score = float(min_relevance_score)
        self.min_relevant_ratio = max(0.0, min(1.0, float(min_relevant_ratio)))

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {
            token for token in re.findall(r"[a-zA-Z0-9]+", (text or "").lower())
            if len(token) > 2 and token not in STOP_WORDS
        }

    def create_plan(self, topic: str, requested_papers: int) -> dict:
        """Build a transparent, deterministic plan without an extra LLM call."""
        topic = (topic or "").strip()
        return {
            "topic": topic,
            "requested_papers": int(requested_papers),
            "evidence_targets": [
                "methodology and model/approach",
                "dataset and experimental setup",
                "reported results and evaluation metrics",
                "author-stated limitations and future work",
            ],
            "initial_query": topic,
            "adaptive_search_budget": self.max_adaptive_searches,
            "stopping_policy": (
                "Stop after at most one adaptive search; never claim a gap is novel "
                "unless independently verified."
            ),
        }

    def evaluate_retrieval(self, topic: str, papers: list[dict], requested: int) -> dict:
        """Evaluate coverage AND per-paper relevance; coverage alone can mislead."""
        topic_tokens = self._tokens(topic)
        title_abstract_tokens = set()
        per_paper_overlaps = []
        low_relevance_titles = []
        relevant_count = 0
        scored_count = 0

        for paper in papers:
            text = f"{paper.get('title', '')} {paper.get('abstract', '')}"
            paper_tokens = self._tokens(text)
            title_abstract_tokens.update(paper_tokens)
            if topic_tokens:
                per_paper_overlaps.append(len(topic_tokens & paper_tokens) / len(topic_tokens))

            score_value = paper.get("relevance_score")
            try:
                score = float(score_value) if score_value is not None else None
            except (TypeError, ValueError):
                score = None
            if score is not None:
                scored_count += 1
                if score >= self.min_relevance_score:
                    relevant_count += 1
                else:
                    low_relevance_titles.append({
                        "title": paper.get("title", "Untitled"),
                        "score": round(score, 4),
                    })

        coverage = (
            len(topic_tokens & title_abstract_tokens) / len(topic_tokens)
            if topic_tokens else 1.0
        )
        mean_overlap = sum(per_paper_overlaps) / len(per_paper_overlaps) if per_paper_overlaps else 0.0
        scores = [float(p["relevance_score"]) for p in papers if p.get("relevance_score") is not None]
        mean_relevance = sum(scores) / len(scores) if scores else 0.0
        relevant_ratio = relevant_count / scored_count if scored_count else 0.0
        shortfall = len(papers) < requested
        weak_coverage = bool(papers) and coverage < self.min_topic_overlap
        weak_relevance = scored_count > 0 and relevant_ratio < self.min_relevant_ratio
        no_scores = bool(papers) and scored_count == 0
        needs_adaptation = (
            shortfall or weak_coverage or weak_relevance or no_scores or not papers
        )

        reasons = []
        if not papers:
            reasons.append("No papers retrieved")
        if shortfall:
            reasons.append(f"Only {len(papers)} of {requested} requested papers retrieved")
        if weak_coverage:
            reasons.append(f"Low lexical topic coverage ({coverage:.2f})")
        if weak_relevance:
            reasons.append(
                f"Only {relevant_count}/{scored_count} papers met relevance threshold "
                f"{self.min_relevance_score:.2f}"
            )
        if no_scores:
            reasons.append("Paper relevance scores are unavailable")

        return {
            "paper_count": len(papers),
            "requested_papers": requested,
            "topic_token_coverage": round(coverage, 3),
            "mean_per_paper_topic_overlap": round(mean_overlap, 3),
            "mean_semantic_relevance": round(mean_relevance, 3),
            "relevant_paper_count": relevant_count,
            "scored_paper_count": scored_count,
            "relevant_paper_ratio": round(relevant_ratio, 3),
            "low_relevance_papers": low_relevance_titles,
            "needs_adaptation": needs_adaptation,
            "reasons": reasons,
        }

    @staticmethod
    def choose_adaptive_query(topic: str, papers: list[dict]) -> str:
        """Choose one broad supplementary query based on what the current set lacks."""
        abstracts = " ".join(
            f"{p.get('title', '')} {p.get('abstract', '')}" for p in papers
        ).lower()
        if not any(word in abstracts for word in ("dataset", "benchmark", "corpus", "data set")):
            suffix = " dataset benchmark evaluation"
        elif not any(word in abstracts for word in ("limitation", "future work", "challenge", "drawback")):
            suffix = " limitations challenges future work"
        else:
            suffix = " methods experiments evaluation"
        return f"{topic.strip()}{suffix}".strip()

    @staticmethod
    def merge_unique(existing: list[dict], additional: list[dict]) -> list[dict]:
        merged = []
        seen = set()
        for paper in [*existing, *additional]:
            url = str(paper.get("url") or paper.get("entry_id") or "").strip().lower()
            title = " ".join(str(paper.get("title") or "").lower().split())
            key = url or title
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(dict(paper))
        return merged

    @staticmethod
    def rerank_for_original_topic(topic: str, papers: list[dict], embedder) -> list[dict]:
        """Recompute comparable BGE scores against the user's original topic."""
        if not papers:
            return papers
        try:
            query = embedder.embed_query(topic)
            docs = embedder.embed_documents([
                f"Title: {p.get('title', '')}\nAbstract: {p.get('abstract', '')}"
                for p in papers
            ])
            import numpy as np
            q = np.asarray(query, dtype=np.float32).reshape(-1)
            d = np.asarray(docs, dtype=np.float32)
            if d.ndim == 1:
                d = d.reshape(1, -1)
            denom = np.linalg.norm(d, axis=1) * max(float(np.linalg.norm(q)), 1e-12)
            denom[denom == 0] = 1e-12
            scores = np.dot(d, q) / denom
            for paper, score in zip(papers, scores):
                paper["relevance_score"] = round(float(score), 4)
                paper["relevance_method"] = "BGE cosine similarity against original research topic"
        except Exception as exc:
            # Keep the already available scores if re-ranking cannot be performed.
            print(f"  Adaptive re-ranking skipped: {exc}")
        return sorted(papers, key=lambda p: float(p.get("relevance_score", 0.0) or 0.0), reverse=True)

    @staticmethod
    def evaluate_extraction(analyses: list[dict]) -> dict:
        """Measure explicit field completeness; missing values remain missing."""
        fields = (
            "methodology", "dataset", "results_metrics",
            "author_stated_limitations", "future_work",
        )
        missing_markers = (
            "not explicitly reported", "not reported", "not available",
            "unavailable", "not found", "n/a", "none",
        )
        total = len(analyses) * len(fields)
        missing = 0
        per_field = {field: {"reported": 0, "missing": 0} for field in fields}
        for analysis in analyses:
            for field in fields:
                value = analysis.get(field)
                is_missing = value is None or not str(value).strip() or any(
                    marker in str(value).strip().lower() for marker in missing_markers
                )
                per_field[field]["missing" if is_missing else "reported"] += 1
                missing += int(is_missing)
        completeness = ((total - missing) / total) if total else 0.0
        return {
            "papers_analyzed": len(analyses),
            "fields_checked": list(fields),
            "field_status": per_field,
            "completeness_ratio": round(completeness, 3),
            "missing_field_count": missing,
            "total_field_count": total,
            "decision": "proceed_with_caveats" if missing else "proceed",
            "note": (
                "Missing fields are reported as missing; they are not inferred or fabricated."
            ),
        }

    @staticmethod
    def record_action(trace: list[dict], action: str, reason: str, details=None) -> None:
        trace.append({"step": len(trace) + 1, "action": action, "reason": reason, "details": details or {}})
