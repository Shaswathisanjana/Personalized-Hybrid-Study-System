"""Extract candidate challenge/limitation sentences from full-text sections."""
import re

LIMITATION_PATTERNS = [
    r"\blimited\b", r"\blimitation\b", r"\bhowever\b", r"\bchallenge\b",
    r"\bchallenging\b", r"\bremains\b", r"\bshortcoming\b", r"\bfuture work\b",
    r"\bfurther work\b", r"\bneed(?:s)? to\b", r"\black of\b", r"\bscarcity\b",
    r"\binsufficient\b", r"\bsmall dataset\b", r"\bcomputational cost\b",
    r"\bgeneralizability\b", r"\bdoes not\b", r"\bdo not\b", r"\bcannot\b",
    r"\bfuture direction\b", r"\bnot address\b", r"\bremain(?:s)? an open\b",
]


def split_sentences(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 35]


def extract_candidate_sentences(paper):
    """Prefer limitations/future-work sections; fall back to results/discussion and abstract."""
    sections = paper.get("sections") or {}
    source_texts = []
    for category in ("limitations", "future_work", "results", "other"):
        for section in sections.get(category, [])[:3]:
            text = section.get("text", "")
            if text:
                source_texts.append(text)
    if not source_texts and paper.get("abstract"):
        source_texts = [paper["abstract"]]
    candidates = []
    seen = set()
    for source in source_texts:
        for sentence in split_sentences(source):
            low = sentence.lower()
            if any(re.search(pattern, low) for pattern in LIMITATION_PATTERNS):
                normalized = re.sub(r"\s+", " ", sentence)
                if normalized not in seen:
                    seen.add(normalized)
                    candidates.append(normalized)
    return candidates[:12]
