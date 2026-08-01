"""
Vector store for retrieved papers, using Chroma with local sentence-transformer
embeddings (no external embedding API needed -> works offline / no extra cost).

This also doubles as the data source for the "activity dashboard" — every
query and paper we store here can be counted/plotted later.
"""
import chromadb
from chromadb.utils import embedding_functions

_client = chromadb.PersistentClient(path="./chroma_store")

_embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

_collection = _client.get_or_create_collection(
    name="papers", embedding_function=_embedding_fn
)


def add_papers(topic: str, papers: list[dict]) -> None:
    """Store papers (with their generated summary) tagged by the query topic."""
    if not papers:
        return
    ids = [f"{topic}::{p['title']}"[:512] for p in papers]
    documents = [p.get("abstract") or p["title"] for p in papers]
    metadatas = [
        {
            "topic": topic,
            "title": p["title"],
            "year": p.get("year") or 0,
            "url": p.get("url") or "",
        }
        for p in papers
    ]
    # upsert avoids duplicate-id errors on repeat queries
    _collection.upsert(ids=ids, documents=documents, metadatas=metadatas)


def query_activity_log() -> list[dict]:
    """Return everything stored so far, for the dashboard."""
    result = _collection.get(include=["metadatas"])
    return result.get("metadatas", [])
