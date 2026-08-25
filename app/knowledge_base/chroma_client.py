from __future__ import annotations
import logging
from typing import List

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from chromadb.config import Settings as ChromaSettings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.models.paper import PaperExtraction
from configs.settings import settings

logger = logging.getLogger(__name__)


class GeminiEmbeddingFunction(EmbeddingFunction):
    """
    Wraps Google Gemini text-embedding-004 as a ChromaDB EmbeddingFunction.
    Uses the Gemini API — no local torch/onnxruntime DLL needed.
    Free with the same GOOGLE_API_KEY used for the LLM.
    """

    def __init__(self):
        self._model = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=settings.GOOGLE_API_KEY,
        )

    def __call__(self, input: Documents) -> Embeddings:
        return self._model.embed_documents(list(input))

    def embed_query(self, text: str) -> List[float]:
        return self._model.embed_query(text)


def _build_embeddings() -> GeminiEmbeddingFunction:
    """Google Gemini embeddings — free, no local ML dependencies."""
    return GeminiEmbeddingFunction()


class KnowledgeBase:
    CHUNKS_COLLECTION      = "paper_chunks"
    EXTRACTIONS_COLLECTION = "paper_extractions"

    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        # Lazy-load embeddings so startup is fast
        self._embeddings: GeminiEmbeddingFunction | None = None

        self.chunks = self.client.get_or_create_collection(
            name=self.CHUNKS_COLLECTION,
            metadata={"hnsw:space": "cosine"},
            embedding_function=self.embeddings,
        )
        self.extractions = self.client.get_or_create_collection(
            name=self.EXTRACTIONS_COLLECTION,
            metadata={"hnsw:space": "cosine"},
            embedding_function=self.embeddings,
        )

    @property
    def embeddings(self) -> GeminiEmbeddingFunction:
        if self._embeddings is None:
            logger.info("Loading Gemini embedding model…")
            self._embeddings = _build_embeddings()
        return self._embeddings


    # ── Chunks ──────────────────────────────────────────────────────────

    def upsert_chunks(
        self,
        paper_id: str,
        title: str,
        authors: list[str],
        year: int | None,
        doi: str,
        source: str,
        report_id: str,
        chunks: list[str],
    ) -> None:
        if not chunks:
            return
        ids       = [f"{paper_id}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "paper_id":    paper_id,
                "title":       title,
                "authors":     ", ".join(authors[:10]),
                "year":        year or 0,
                "doi":         doi or "",
                "source":      source,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "report_id":   report_id,
            }
            for i in range(len(chunks))
        ]
        self.chunks.upsert(
            ids=ids, documents=chunks, metadatas=metadatas
        )
        logger.debug(f"KB: upserted {len(chunks)} chunks for {paper_id}")

    def retrieve_chunks(
        self,
        query: str,
        report_id: str,
        n_results: int = 10,
        paper_ids: list[str] | None = None,
    ) -> list[dict]:
        query_vec = self.embeddings.embed_query(query)
        where: dict = {"report_id": report_id}
        if paper_ids:
            where["paper_id"] = {"$in": paper_ids}

        count = self.chunks.count()
        if count == 0:
            return []

        results = self.chunks.query(
            query_embeddings=[query_vec],
            n_results=min(n_results, count),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        return [
            {
                "text":     doc,
                "metadata": meta,
                "score":    max(0.0, 1.0 - dist),
            }
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            )
        ]

    # ── Extractions ─────────────────────────────────────────────────────

    def upsert_extraction(self, extraction: PaperExtraction, report_id: str) -> None:
        embed_text = " | ".join(filter(None, [
            extraction.problem_statement,
            extraction.objective,
            extraction.methodology,
            extraction.results_summary,
            " ".join(extraction.keywords),
        ])) or extraction.title

        vector = self.embeddings.embed_query(embed_text)
        self.extractions.upsert(
            ids=[f"{extraction.paper_id}_extraction"],
            embeddings=[vector],
            documents=[extraction.model_dump_json()],
            metadatas=[{
                "paper_id":    extraction.paper_id,
                "title":       extraction.title,
                "year":        extraction.year or 0,
                "keywords":    ", ".join(extraction.keywords),
                "has_full_pdf": extraction.extraction_confidence > 0.5,
                "report_id":   report_id,
            }],
        )

    def get_all_extractions(self, report_id: str) -> list[PaperExtraction]:
        try:
            results = self.extractions.get(
                where={"report_id": report_id},
                include=["documents"],
            )
            return [
                PaperExtraction.model_validate_json(doc)
                for doc in results.get("documents", [])
            ]
        except Exception as e:
            logger.warning(f"KB: get_all_extractions failed: {e}")
            return []
