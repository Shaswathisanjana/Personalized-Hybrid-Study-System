from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class QARequest(BaseModel):
    report_id: str
    question: str
    mode: str = Field(
        default="general",
        description="general | explain_paper | compare_papers | summarize_section | explain_term",
    )
    paper_ids: Optional[list[str]] = None


class RetrievedChunk(BaseModel):
    text: str
    paper_id: str
    paper_title: str
    relevance_score: float


class QAResponse(BaseModel):
    question: str
    answer: str
    sources: list[RetrievedChunk] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    grounded: bool = True
