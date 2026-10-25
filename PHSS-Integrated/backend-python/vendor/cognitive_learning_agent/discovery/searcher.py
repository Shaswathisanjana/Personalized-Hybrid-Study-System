"""Web Search using DuckDuckGo Search (ddgs) to discover learning resources."""

import logging
import warnings
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

warnings.filterwarnings("ignore", category=RuntimeWarning)

from cognitive_learning_agent.config import settings
from cognitive_learning_agent.models.schemas import LearningFormat, DifficultyLevel

logger = logging.getLogger(__name__)


class ResourceSearcher:
    """Discovers real online learning materials using DuckDuckGo Search."""

    def __init__(self, max_results: int = settings.MAX_SEARCH_RESULTS_PER_QUERY):
        self.max_results = max_results
        self._search_cache: Dict[str, List[Dict[str, Any]]] = {}

    def search_for_concept(
        self,
        concept_name: str,
        goal: str,
        preferred_format: LearningFormat = LearningFormat.ANY,
        difficulty: DifficultyLevel = DifficultyLevel.BEGINNER,
        preferred_language: str = "Python",
    ) -> List[Dict[str, Any]]:
        """Run targeted queries to find tutorials, videos, docs, and practice problems."""
        cache_key = f"{goal}:{concept_name}:{preferred_format.value}:{difficulty.value}:{preferred_language}"
        if cache_key in self._search_cache:
            return self._search_cache[cache_key]

        query_variants = self._build_queries(
            concept_name, goal, preferred_format, difficulty, ""
        )

        raw_results = []
        seen_urls = set()

        for q in query_variants:
            try:
                results = self._execute_ddg_search(q, max_results=self.max_results)
                for r in results:
                    url = r.get("href") or r.get("link") or r.get("url")
                    if not url or url in seen_urls:
                        continue
                    if self._is_blacklisted(url):
                        continue

                    # Filter out non-educational lifestyle / food / tourism spam
                    title_lower = (r.get("title", "") or "").lower()
                    body_lower = (r.get("body", "") or r.get("snippet", "") or "").lower()
                    combined_text = f"{title_lower} {body_lower}"
                    spam_indicators = ["recipe", "food", "dishes", "restaurant", "hotel", "flight", "tourism", "vacation", "cuisine", "shopping"]
                    if any(sk in combined_text for sk in spam_indicators):
                        continue

                    # Verify relevance: require at least one meaningful topic keyword
                    import re
                    c_tokens = [w for w in re.findall(r"[a-z0-9]+", concept_name.lower()) if len(w) > 3 and w not in ["tutorial", "guide", "learn", "fundamentals", "intermediate", "advanced", "overview", "remediation", "introduction"]]
                    if c_tokens and not any(ct in combined_text for ct in c_tokens):
                        continue

                    import re
                    goal_tokens = [t for t in re.findall(r"[a-z]+", goal.lower()) if len(t)>3 and t not in {"want","wanted","learn","learning","understand","topic","master","build","personalized","path","basics","from","step","with","this","that","help","roadmap"}]
                    if goal_tokens and not any(re.search(r"\b"+re.escape(t)+r"\b", combined_text) for t in goal_tokens):
                        continue
                    seen_urls.add(url)
                    raw_results.append(
                        {
                            "url": url,
                            "title": r.get("title", ""),
                            "snippet": r.get("body", "") or r.get("snippet", ""),
                            "search_query": q,
                            "concept": concept_name,
                        }
                    )
                if len(raw_results) >= 2:
                    break
            except Exception as e:
                logger.warning(f"Live search skipped for '{q}': {e}. Using curated educational resources.")
                break

        # If live search returned very few (e.g. rate limit), provide curated high-quality authoritative resources
        if len(raw_results) < 2:
            raw_results.extend(self._get_curated_fallback(concept_name, ""))

        self._search_cache[cache_key] = raw_results
        return raw_results

    def _build_queries(
        self,
        concept_name: str,
        goal: str,
        preferred_format: LearningFormat,
        difficulty: DifficultyLevel,
        preferred_language: str,
    ) -> List[str]:
        """Construct diversified queries targeting authoritative learning sources."""
        queries = []
        lang_str = f"{preferred_language} " if preferred_language else ""

        # Format modifiers
        if preferred_format == LearningFormat.VIDEO:
            queries.append(f"{lang_str}{concept_name} video tutorial site:youtube.com")
            queries.append(f"{lang_str}{concept_name} explained step by step video")
        elif preferred_format == LearningFormat.DOCUMENTATION:
            queries.append(f"{lang_str}{concept_name} official documentation guide")
            queries.append(f"{lang_str}{concept_name} tutorial documentation")
        elif preferred_format == LearningFormat.INTERACTIVE:
            queries.append(f"{lang_str}{concept_name} interactive tutorial hands on")
        elif preferred_format == LearningFormat.PRACTICE:
            queries.append(f"{lang_str}{concept_name} practice exercises examples problems")
        elif preferred_format == LearningFormat.VISUALIZATION:
            queries.append(f"{concept_name} visual guide animation interactive visualization")
        else:
            # Broad mix
            queries.append(f"{lang_str}{concept_name} tutorial {difficulty.value}")
            queries.append(f"{lang_str}{concept_name} guide best practices")
            queries.append(f"{lang_str}{concept_name} complete walkthrough")

        return queries

    def _execute_ddg_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Call DuckDuckGo search library with strict 2-second timeout."""
        try:
            from ddgs import DDGS
            ddgs = DDGS(timeout=2)
            return list(ddgs.text(query, max_results=max_results))
        except Exception:
            try:
                from duckduckgo_search import DDGS
                ddgs = DDGS(timeout=2)
                return list(ddgs.text(query, max_results=max_results))
            except Exception as e:
                logger.debug(f"ddgs call exception: {e}")
                raise e

    @staticmethod
    def _is_blacklisted(url: str) -> bool:
        """Filter out social media spam, paywalls, and low quality non-educational sites."""
        try:
            domain = urlparse(url).netloc.lower()
            blacklist = [
                "facebook.com",
                "twitter.com",
                "x.com",
                "instagram.com",
                "tiktok.com",
                "pinterest.com",
                "quora.com",
                "reddit.com/r/all",
                ".gov",
                "gov.in",
                "maps.google",
                "books.google",
                "play.google",
                "amazon.",
                "flipkart.",
                "ebay.",
            ]
            return any(b in domain for b in blacklist)
        except Exception:
            return False

    @staticmethod
    def _get_curated_fallback(concept_name: str, language: str) -> List[Dict[str, Any]]:
        """Curated authoritative links if search is blocked or rate-limited."""
        c_lower = concept_name.lower()
        if "async" in c_lower or "event loop" in c_lower:
            return [
                {
                    "url": "https://docs.python.org/3/library/asyncio.html",
                    "title": "asyncio — Asynchronous I/O Documentation",
                    "snippet": "Official Python asyncio documentation covering event loops, tasks, coroutines, and streams.",
                    "concept": concept_name,
                },
                {
                    "url": "https://realpython.com/async-io-python/",
                    "title": "Async IO in Python: A Complete Walkthrough",
                    "snippet": "A comprehensive hands-on tutorial on async/await syntax, event loops, and non-blocking I/O.",
                    "concept": concept_name,
                },
                {
                    "url": "https://www.geeksforgeeks.org/python/python-async/",
                    "title": "Python Async - GeeksforGeeks",
                    "snippet": "Tutorial explaining Python async concepts, tasks, coroutines, and practical examples.",
                    "concept": concept_name,
                },
            ]
        elif "attention" in c_lower or "transformer" in c_lower:
            return [
                {
                    "url": "https://jalammar.github.io/illustrated-transformer/",
                    "title": "The Illustrated Transformer by Jay Alammar",
                    "snippet": "Visualizing self-attention, multi-head attention, and transformer architecture step-by-step.",
                    "concept": concept_name,
                },
                {
                    "url": "https://arxiv.org/abs/1706.03762",
                    "title": "Attention Is All You Need Paper",
                    "snippet": "Original research paper introducing the Transformer architecture and self-attention.",
                    "concept": concept_name,
                },
            ]
        elif "tree" in c_lower or "bst" in c_lower or "dsa" in c_lower or "traversal" in c_lower:
            if "traversal" in c_lower:
                return [
                    {
                        "url": "https://www.geeksforgeeks.org/tree-traversals-inorder-preorder-and-postorder/",
                        "title": "Tree Traversals (Inorder, Preorder and Postorder)",
                        "snippet": "Comprehensive guide on Depth First Traversals (Inorder, Preorder, Postorder) and Level Order Traversals with code examples.",
                        "concept": concept_name,
                    },
                    {
                        "url": "https://www.programiz.com/dsa/tree-traversal",
                        "title": "Tree Traversal in Data Structures - Programiz",
                        "snippet": "Learn tree traversals with visual diagrams, step-by-step trace, and Python implementation.",
                        "concept": concept_name,
                    },
                ]
            elif "search" in c_lower or "bst" in c_lower:
                return [
                    {
                        "url": "https://www.geeksforgeeks.org/binary-search-tree-data-structure/",
                        "title": "Binary Search Tree (BST) Data Structure - GeeksforGeeks",
                        "snippet": "In-depth guide covering BST properties, search, insertion, deletion operations, and time complexities.",
                        "concept": concept_name,
                    },
                    {
                        "url": "https://www.programiz.com/dsa/binary-search-tree",
                        "title": "Binary Search Tree (BST) - Programiz Guide",
                        "snippet": "Clear visual tutorial on how binary search trees operate with full Python code.",
                        "concept": concept_name,
                    },
                ]
            elif "avl" in c_lower or "balanc" in c_lower:
                return [
                    {
                        "url": "https://www.geeksforgeeks.org/introduction-to-avl-tree/",
                        "title": "Introduction to AVL Tree - GeeksforGeeks",
                        "snippet": "Self-balancing binary search trees: balance factor, LL, RR, LR, RL rotations explained with diagrams.",
                        "concept": concept_name,
                    },
                    {
                        "url": "https://www.programiz.com/dsa/avl-tree",
                        "title": "AVL Tree with Rotations - Programiz",
                        "snippet": "Visual guide to self-balancing AVL trees and rotation operations.",
                        "concept": concept_name,
                    },
                ]
            else:
                return [
                    {
                        "url": "https://www.geeksforgeeks.org/introduction-to-tree-data-structure/",
                        "title": "Introduction to Tree Data Structure - GeeksforGeeks",
                        "snippet": "Foundational guide explaining tree terminology (root, child, leaf, height, depth), types, and applications.",
                        "concept": concept_name,
                    },
                    {
                        "url": "https://www.geeksforgeeks.org/binary-tree-data-structure/",
                        "title": "Binary Tree Data Structure - Complete Guide",
                        "snippet": "Comprehensive overview of Binary Trees, representations, traversals, and common practice problems.",
                        "concept": concept_name,
                    },
                    {
                        "url": "https://www.programiz.com/dsa/trees",
                        "title": "Tree Data Structure Explained - Programiz",
                        "snippet": "Beginner friendly guide to non-linear hierarchical tree structures with illustrations.",
                        "concept": concept_name,
                    },
                ]
        elif "fastapi" in c_lower or "rest" in c_lower or "api" in c_lower:
            return [
                {
                    "url": "https://fastapi.tiangolo.com/tutorial/",
                    "title": "FastAPI Tutorial - User Guide",
                    "snippet": "Step-by-step official tutorial covering path operations, Pydantic models, and REST endpoints.",
                    "concept": concept_name,
                },
                {
                    "url": "https://realpython.com/fastapi-python-web-apis/",
                    "title": "Using FastAPI to Build Python Web APIs",
                    "snippet": "Practical guide to building performant RESTful APIs with FastAPI and SQLite.",
                    "concept": concept_name,
                },
            ]
        else:
            return []
