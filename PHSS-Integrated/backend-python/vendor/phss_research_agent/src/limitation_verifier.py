"""Bounded follow-up search to verify whether extracted research limitations have been addressed.

This module deliberately does not declare a limitation resolved from title/abstract similarity
alone. It returns candidate follow-up papers and conservative evidence statuses. Search budgets
are global and per limitation, and results are cached on disk to reduce repeated API calls.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from .arxiv_search import search_arxiv, is_survey_paper


def _norm(text: Any) -> str:
    if text is None:
        return ""
    if isinstance(text, (list, tuple, set)):
        return " ".join(_norm(x) for x in text)
    if isinstance(text, dict):
        return " ".join(f"{k}: {_norm(v)}" for k, v in text.items())
    return re.sub(r"\s+", " ", str(text)).strip()


def _limitation_items(paper_analyses: list[dict], max_items: int = 8) -> list[dict]:
    """Extract limitation-like fields from analyzer output without assuming one schema."""
    found, seen = [], set()
    labels = ("limitation", "weakness", "challenge", "future work", "future_work", "shortcoming")

    def walk(obj, paper_title="", paper_url="", path=""):
        if isinstance(obj, dict):
            title = _norm(obj.get("title") or obj.get("paper_title") or paper_title)
            url = _norm(obj.get("url") or obj.get("paper_url") or paper_url)
            for key, value in obj.items():
                key_s = str(key).lower().replace("-", "_")
                if any(label.replace(" ", "_") in key_s or label in key_s for label in labels):
                    values = value if isinstance(value, list) else [value]
                    for item in values:
                        text = _norm(item)
                        if len(text) < 25 or text.lower() in {"not reported", "n/a", "none", "unknown"}:
                            continue
                        sig = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
                        if sig and sig not in seen:
                            seen.add(sig)
                            found.append({"limitation": text, "source_paper": title or "Unknown", "source_url": url, "field": f"{path}.{key}".strip(".")})
                else:
                    walk(value, title, url, f"{path}.{key}".strip("."))
        elif isinstance(obj, list):
            for i, value in enumerate(obj):
                walk(value, paper_title, paper_url, f"{path}[{i}]")

    for item in paper_analyses or []:
        walk(item)
        if len(found) >= max_items:
            break
    return found[:max_items]


def _queries(topic: str, limitation: str) -> list[str]:
    """Generate a small deterministic query set; no LLM calls or unbounded query loops."""
    clean = re.sub(r"[^A-Za-z0-9 +\-]", " ", limitation)
    words = [w for w in re.findall(r"[A-Za-z0-9]+", clean) if len(w) > 3]
    stop = {"that", "with", "from", "this", "these", "those", "their", "there", "have", "been", "were", "which", "when", "using", "based", "paper", "study", "method", "methods", "limitation", "limited", "lack", "lackof"}
    keywords = []
    for word in words:
        if word.lower() not in stop and word.lower() not in {x.lower() for x in keywords}:
            keywords.append(word)
        if len(keywords) >= 7:
            break
    phrase = " ".join(keywords[:5]) or limitation[:80]
    return [f"{topic} {phrase}", f"{topic} improvement {phrase}"]


def _paper_key(paper: dict) -> str:
    identity = _norm(paper.get("url") or paper.get("doi") or paper.get("title")).lower()
    return hashlib.sha1(identity.encode("utf-8")).hexdigest()


def _candidate_status(limitation: str, papers: list[dict]) -> str:
    """Conservative preliminary status; full-text evidence is required for resolution claims."""
    if not papers:
        return "insufficient_evidence_no_relevant_followup_found"
    return "candidate_followup_papers_found_full_text_verification_required"


class LimitationVerifier:
    """Search for follow-up work under strict global and per-limitation budgets."""
    def __init__(self, cache_path=None):
        self.max_rounds_per_limitation = max(1, int(os.getenv("PHSS_VERIFY_MAX_ROUNDS_PER_LIMITATION", "2")))
        self.max_papers_per_limitation = max(1, int(os.getenv("PHSS_VERIFY_MAX_PAPERS_PER_LIMITATION", "5")))
        self.max_total_papers = max(1, int(os.getenv("PHSS_VERIFY_MAX_TOTAL_PAPERS", "20")))
        self.max_total_rounds = max(1, int(os.getenv("PHSS_VERIFY_MAX_TOTAL_ROUNDS", "2")))
        self.max_limitations = max(1, int(os.getenv("PHSS_VERIFY_MAX_LIMITATIONS", "2")))
        self.cache_path = Path(cache_path or os.getenv("PHSS_VERIFY_CACHE", "outputs/limitation_search_cache.json"))
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.cache = json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self.cache = {}

    def _save_cache(self):
        temp = self.cache_path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.cache, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(self.cache_path)

    def verify(self, topic: str, paper_analyses: list[dict]) -> dict:
        limitations = _limitation_items(paper_analyses, self.max_limitations)
        results = []
        total_rounds = 0
        all_papers = {}
        stopped_reason = "all_selected_limitations_processed"

        for item in limitations:
            if total_rounds >= self.max_total_rounds:
                stopped_reason = "global_search_round_budget_exhausted"
                break
            limitation = item["limitation"]
            candidates = {}
            queries_used = []
            rounds_for_item = 0
            for query in _queries(topic, limitation)[:self.max_rounds_per_limitation]:
                if total_rounds >= self.max_total_rounds:
                    stopped_reason = "global_search_round_budget_exhausted"
                    break
                if len(all_papers) >= self.max_total_papers:
                    stopped_reason = "global_unique_paper_budget_exhausted"
                    break
                qkey = hashlib.sha1(query.lower().encode("utf-8")).hexdigest()
                queries_used.append(query)
                total_rounds += 1
                rounds_for_item += 1
                if qkey in self.cache:
                    found = self.cache[qkey]
                    source = "cache"
                else:
                    try:
                        time.sleep(1.0)
                        found = search_arxiv(query, min(self.max_papers_per_limitation, self.max_total_papers))
                        found = [p for p in found if not is_survey_paper(str(p.get("title", "")), str(p.get("abstract", "")))]
                        self.cache[qkey] = found
                        self._save_cache()
                        source = "arxiv"
                    except Exception as exc:
                        found = []
                        source = "error"
                        print(f"  Limitation search failed for query '{query}': {exc}")
                        if "429" in str(exc) or "rate" in str(exc).lower():
                            stopped_reason = "arxiv_rate_limited"
                            break
                for paper in found:
                    key = _paper_key(paper)
                    if not key or key in all_papers:
                        continue
                    if len(all_papers) >= self.max_total_papers:
                        break
                    all_papers[key] = paper
                    candidates[key] = paper
                if len(candidates) >= self.max_papers_per_limitation:
                    break
                # Do not keep searching if this query produced no new candidates.
                if not found:
                    continue
            selected = list(candidates.values())[:self.max_papers_per_limitation]
            results.append({
                **item,
                "queries_used": queries_used,
                "search_rounds_used": rounds_for_item,
                "followup_papers": selected,
                "status": _candidate_status(limitation, selected),
                "status_note": "This is retrieval-level evidence only. Do not interpret it as proof that the limitation is solved or remains open; inspect full text and comparable experiments.",
            })
            if stopped_reason in {"global_search_round_budget_exhausted", "global_unique_paper_budget_exhausted"}:
                break

        self._save_cache()
        return {
            "enabled": True,
            "budget": {
                "max_rounds_per_limitation": self.max_rounds_per_limitation,
                "max_papers_per_limitation": self.max_papers_per_limitation,
                "max_total_unique_papers": self.max_total_papers,
                "max_total_search_rounds": self.max_total_rounds,
                "max_limitations": self.max_limitations,
            },
            "limitations_considered": len(limitations),
            "limitations_processed": len(results),
            "total_search_rounds_used": total_rounds,
            "total_unique_followup_papers": len(all_papers),
            "stopped_reason": stopped_reason,
            "results": results,
            "important_note": "Statuses are deliberately conservative. Follow-up retrieval alone cannot establish that a limitation was addressed; use full-text methodology and experimental evidence before upgrading a status.",
        }
