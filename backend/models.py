from pydantic import BaseModel
from typing import List, Optional


class QueryRequest(BaseModel):
    query: str
    max_papers: int = 8


class PaperSummary(BaseModel):
    title: str
    authors: List[str]
    year: Optional[int]
    url: Optional[str]
    abstract: Optional[str]
    summary: str


class ResearchResponse(BaseModel):
    topic: str
    papers: List[PaperSummary]
    comparison_table_markdown: str


class OrchestratorRequest(BaseModel):
    query: str
    num_papers: int=3


class OrchestratorResponse(BaseModel):
    routed_to: str
    result: dict
