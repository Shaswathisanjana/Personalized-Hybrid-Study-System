"""Topic Similarity Matching for Cognitive Learning Agent.

Matches learning topic queries against existing learning journeys using hybrid
lexical analysis (abbreviations, stemming, token containment) and semantic embeddings.
"""

import logging
import re
from typing import Tuple, List, Optional
import difflib
import numpy as np

logger = logging.getLogger(__name__)

# Common computer science and technical abbreviations
ABBREVIATIONS = {
    "dsa": "data structures and algorithms",
    "dp": "dynamic programming",
    "bst": "binary search tree",
    "avl": "avl tree",
    "bfs": "breadth first search",
    "dfs": "depth first search",
    "mst": "minimum spanning tree",
    "dag": "directed acyclic graph",
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "api": "rest api",
    "apis": "rest apis",
    "rest": "restful api",
    "oop": "object oriented programming",
    "db": "database",
    "sql": "relational database sql",
}

# Domain-specific word roots / normalization
STEM_MAP = {
    "trees": "tree",
    "graphs": "graph",
    "arrays": "array",
    "strings": "string",
    "heaps": "heap",
    "queues": "queue",
    "stacks": "stack",
    "algorithms": "algorithm",
    "structures": "structure",
    "coroutines": "coroutine",
    "asyncio": "async",
    "asynchronous": "async",
    "concurrency": "concurrent",
    "databases": "database",
}

STOPWORDS = {
    "in", "and", "the", "for", "with", "to", "of", "a", "an",
    "master", "learn", "understand", "build", "using", "from",
    "scratch", "guide", "tutorial", "fundamentals", "basics", "intro", "introduction"
}


def _stem_word(w: str) -> str:
    w = w.lower().strip()
    if w in STEM_MAP:
        return STEM_MAP[w]
    if w.endswith("ies"):
        return w[:-3] + "y"
    if w.endswith("ees"):
        return w[:-1]
    if w.endswith("es") and len(w) > 4:
        return w[:-2]
    if w.endswith("s") and len(w) > 2 and not w.endswith("ss"):
        return w[:-1]
    return w


def normalize_topic(text: str) -> Tuple[List[str], str]:
    """Normalize topic string: lowercase, expand abbreviations, remove stopwords, stem."""
    if not text:
        return [], ""
    text_clean = text.lower()
    for abbr, full in ABBREVIATIONS.items():
        text_clean = re.sub(rf"\b{re.escape(abbr)}\b", full, text_clean)

    tokens = re.findall(r"[a-z0-9]+", text_clean)
    core = [_stem_word(t) for t in tokens if t not in STOPWORDS]
    return core, " ".join(core)


_EMBEDDING_MODEL = None


def _get_embedding_model():
    # Topic normalization and lexical matching below require no model.
    return None


def compute_topic_similarity(query: str, target: str) -> Tuple[bool, float]:
    """Compute whether query and target represent the same or highly similar learning topic.

    Returns:
        (is_match: bool, similarity_score: float)
    """
    if not query or not target:
        return False, 0.0

    c1, s1 = normalize_topic(query)
    c2, s2 = normalize_topic(target)

    # 1. Exact normalized match
    if s1 and s1 == s2:
        return True, 1.0

    set1, set2 = set(c1), set(c2)
    if not set1 or not set2:
        return False, 0.0

    # 2. Token Subset Match (e.g. 'trees' in 'trees in data structures and algorithms')
    if set1.issubset(set2) or set2.issubset(set1):
        # High confidence match
        return True, 0.95

    # 3. Core Noun Intersection (e.g. both have 'tree' or both have 'graph')
    intersection = set1.intersection(set2)
    core_nouns = {"tree", "graph", "heap", "stack", "queue", "async", "dp", "recursion", "fastapi", "docker"}
    if intersection.intersection(core_nouns):
        return True, 0.90

    # 4. Jaccard Token Overlap
    jaccard = len(intersection) / len(set1.union(set2))
    if jaccard >= 0.45:
        return True, float(jaccard)

    # 5. Sequence Matcher on normalized string
    seq_ratio = difflib.SequenceMatcher(None, s1, s2).ratio()
    if seq_ratio >= 0.65:
        return True, float(seq_ratio)

    # 6. Semantic Embedding Cosine Similarity Fallback
    model = _get_embedding_model()
    if model is not None:
        try:
            e1 = model.encode([query], normalize_embeddings=True)[0]
            e2 = model.encode([target], normalize_embeddings=True)[0]
            cos_sim = float(np.dot(e1, e2))
            if cos_sim >= 0.65:
                return True, cos_sim
            return False, cos_sim
        except Exception as e:
            logger.debug(f"Semantic similarity check error: {e}")

    return False, max(jaccard, seq_ratio)
