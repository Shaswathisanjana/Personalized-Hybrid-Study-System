from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class PaperMetadata(BaseModel):
    """Raw metadata returned by the Search Agent."""
    paper_id: str = Field(..., description="Unique ID — DOI or source-specific")
    title: str
    authors: list[str]
    year: Optional[int] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    pdf_url: Optional[str] = None
    source_url: Optional[str] = None
    citation_count: Optional[int] = None
    source: str = Field(..., description="semantic_scholar | arxiv | openalex | crossref")
    keywords: list[str] = Field(default_factory=list)
    venue: Optional[str] = None


class PaperExtraction(BaseModel):
    """Structured information extracted by the Reading Agent."""
    model_config = ConfigDict(protected_namespaces=())

    paper_id: str
    title: str
    authors: list[str]
    year: Optional[int] = None
    doi: Optional[str] = None

    # Core content
    problem_statement: Optional[str] = None
    objective: Optional[str] = None
    datasets_used: list[str] = Field(default_factory=list)
    dataset_size: Optional[str] = None
    methodology: Optional[str] = None
    model_architecture: Optional[str] = None
    results_summary: Optional[str] = None
    evaluation_metrics: list[str] = Field(default_factory=list)
    limitations: Optional[str] = None
    future_work: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)

    # ML-specific details (from notebook schema)
    domain: Optional[str] = None
    backbone: Optional[str] = None
    optimizer: Optional[str] = None
    loss_function: Optional[str] = None
    epochs: Optional[str] = None
    batch_size: Optional[str] = None
    advantages: list[str] = Field(default_factory=list)
    novel_contributions: list[str] = Field(default_factory=list)

    # Numeric results for comparison table
    accuracy: Optional[str] = None
    precision: Optional[str] = None
    recall: Optional[str] = None
    f1_score: Optional[str] = None
    map_score: Optional[str] = None   # mAP

    extraction_confidence: float = Field(
        default=1.0, ge=0.0, le=1.0,
        description="0.0 = abstract-only, 1.0 = full PDF"
    )
    chroma_doc_id: Optional[str] = None
