"""Semantic Ranking and Difficulty Alignment for Learning Resources."""

import logging
from typing import List, Dict, Any, Optional
import numpy as np

from cognitive_learning_agent.config import settings
from cognitive_learning_agent.models.schemas import (
    LearningResource,
    DifficultyLevel,
    LearningFormat,
)

logger = logging.getLogger(__name__)


_SHARED_EMBEDDING_MODELS: Dict[str, Any] = {}


class ResourceRanker:
    """Ranks educational resources based on semantic embeddings, difficulty calibration, and format preference."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.FALLBACK_EMBEDDING_MODEL
        self._embedding_model = None
        self._load_embedding_model()

    def _load_embedding_model(self):
        """Use lexical relevance; no local model or Hub download."""
        self._embedding_model = None

    def rank_resources(
        self,
        candidate_items: List[Dict[str, Any]],
        target_concept: str,
        learning_goal: str,
        learner_level: DifficultyLevel = DifficultyLevel.BEGINNER,
        preferred_format: LearningFormat = LearningFormat.ANY,
    ) -> List[LearningResource]:
        """Rank candidates and convert into structured LearningResource objects."""
        if not candidate_items:
            return []

        query_text = f"{target_concept}. Learning goal: {learning_goal}"

        # 1. Compute Semantic Similarity
        semantic_scores = self._compute_semantic_scores(
            query_text, [f"{item.get('title', '')} {item.get('description', '')}" for item in candidate_items]
        )

        ranked_resources: List[LearningResource] = []

        for item, sem_score in zip(candidate_items, semantic_scores):
            raw_url = item["url"]
            domain = item.get("domain", "")
            title = item.get("title", "")
            description = item.get("description", item.get("snippet", ""))
            fmt = item.get("format", LearningFormat.DOCUMENTATION)
            est_minutes = item.get("estimated_minutes", 15)

            # Inferred difficulty of resource
            res_diff = self._infer_difficulty(title, description, domain)

            # Scoring factors
            if preferred_format != LearningFormat.ANY:
                format_bonus = 0.20 if fmt == preferred_format else -0.05
            else:
                format_bonus = 0.05
            authority_bonus = self._domain_authority_bonus(domain)
            difficulty_penalty = self._difficulty_mismatch_penalty(res_diff, learner_level)

            if sem_score <= 0.0:
                final_relevance = 0.0
            else:
                final_relevance = max(
                    0.05,
                    min(
                        0.99,
                        (sem_score * 0.65) + format_bonus + authority_bonus - difficulty_penalty,
                    ),
                )

            # Filter out completely off-topic or irrelevant items
            if final_relevance < 0.35:
                continue

            resource = LearningResource(
                url=raw_url,
                title=title,
                snippet=description,
                domain=domain,
                format=fmt,
                difficulty=res_diff,
                target_concept=target_concept,
                relevance_score=round(float(final_relevance), 3),
                is_valid=item.get("is_valid", True),
                status_code=item.get("status_code", 200),
                estimated_minutes=est_minutes,
                word_count=item.get("word_count", 500),
            )
            ranked_resources.append(resource)

        # Sort descending by relevance score
        ranked_resources.sort(key=lambda r: r.relevance_score, reverse=True)
        return ranked_resources

    def _compute_semantic_scores(self, query: str, texts: List[str]) -> List[float]:
        """Compute cosine similarity scores between query and resource texts."""
        if self._embedding_model is not None and texts:
            try:
                q_emb = self._embedding_model.encode([query], normalize_embeddings=True)[0]
                t_embs = self._embedding_model.encode(texts, normalize_embeddings=True)
                sims = np.dot(t_embs, q_emb)
                # Map [-1, 1] cosine to [0, 1]
                scores = [float(np.clip((s + 1) / 2, 0.1, 1.0)) for s in sims]
                return scores
            except Exception as e:
                logger.debug(f"Embedding scoring failed: {e}. Fallback to lexical.")

        # Lexical Jaccard/overlap fallback
        stopwords = {"in", "and", "the", "for", "with", "to", "of", "a", "an", "is", "on", "at", "by", "learning", "goal", "remediate", "weak", "area"}
        q_tokens = {w for w in query.lower().replace("-", " ").replace("/", " ").split() if w not in stopwords and len(w) > 2}
        scores = []
        for text in texts:
            t_tokens = {w for w in text.lower().replace("-", " ").replace("/", " ").split() if w not in stopwords and len(w) > 2}
            intersection = len(q_tokens.intersection(t_tokens))
            if intersection == 0:
                scores.append(0.0)
                continue
            union = len(q_tokens.union(t_tokens)) or 1
            overlap = intersection / union
            # Overlap scaled between 0.40 and 0.95
            score = 0.40 + min(0.55, overlap * 2.5)
            scores.append(score)
        return scores

    @staticmethod
    def _infer_difficulty(title: str, description: str, domain: str) -> DifficultyLevel:
        combined = f"{title} {description}".lower()
        if any(w in combined for w in ["advanced", "under the hood", "internals", "in-depth", "expert", "optimization", "deep dive"]):
            return DifficultyLevel.ADVANCED
        if any(w in combined for w in ["intermediate", "patterns", "practical", "production", "real-world", "best practices"]):
            return DifficultyLevel.INTERMEDIATE
        return DifficultyLevel.BEGINNER

    @staticmethod
    def _domain_authority_bonus(domain: str) -> float:
        authoritative = [
            "docs.python.org",
            "developer.mozilla.org",
            "realpython.com",
            "geeksforgeeks.org",
            "programiz.com",
            "w3schools.com",
            "freecodecamp.org",
            "baeldung.com",
            "leetcode.com",
            "arxiv.org",
            "fastapi.tiangolo.com",
            "pytorch.org",
            "huggingface.co",
            "github.com",
            "wikipedia.org",
            "jalammar.github.io",
            "youtube.com",
        ]
        if any(auth in domain for auth in authoritative):
            return 0.15
        return 0.0

    @staticmethod
    def _difficulty_mismatch_penalty(res_diff: DifficultyLevel, learner_level: DifficultyLevel) -> float:
        # If learner is beginner and resource is advanced, penalize
        if learner_level == DifficultyLevel.BEGINNER and res_diff == DifficultyLevel.ADVANCED:
            return 0.25
        # If learner is advanced and resource is beginner, slight penalty
        if learner_level == DifficultyLevel.ADVANCED and res_diff == DifficultyLevel.BEGINNER:
            return 0.10
        return 0.0
