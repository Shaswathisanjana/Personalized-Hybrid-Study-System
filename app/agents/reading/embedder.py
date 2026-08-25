from __future__ import annotations
import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.models.paper import PaperMetadata, PaperExtraction
from app.knowledge_base.chroma_client import KnowledgeBase

logger = logging.getLogger(__name__)

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
    separators=["\n\n", "\n", ". ", " "],
)


async def embed_and_store(
    kb: KnowledgeBase,
    extraction: PaperExtraction,
    full_text: str,
    paper: PaperMetadata,
    report_id: str,
) -> None:
    """Chunk text, embed, and upsert into ChromaDB; also store extraction."""
    # Store the structured extraction
    kb.upsert_extraction(extraction, report_id)

    # Store text chunks
    text = full_text or paper.abstract or ""
    if not text.strip():
        return

    chunks = _splitter.split_text(text)
    if not chunks:
        return

    kb.upsert_chunks(
        paper_id=paper.paper_id,
        title=paper.title,
        authors=paper.authors,
        year=paper.year,
        doi=paper.doi or "",
        source=paper.source,
        report_id=report_id,
        chunks=chunks,
    )
    logger.debug(f"Embedder: stored {len(chunks)} chunks for {paper.paper_id}")
