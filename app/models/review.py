from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class MethodComparison(BaseModel):
    aspect: str
    papers: dict[str, str]  # paper_id → description


class LiteratureReview(BaseModel):
    topic: str
    introduction: str
    existing_approaches: str
    method_comparison: list[MethodComparison] = Field(default_factory=list)
    trends: str
    strengths_and_weaknesses: str
    chronological_developments: str
    paper_ids_covered: list[str] = Field(default_factory=list)
    per_paper_analysis: list[dict] = Field(
        default_factory=list,
        description="Structured per-paper breakdown with metrics, methods, datasets, etc."
    )


class ResearchGap(BaseModel):
    gap_type: str
    description: str
    evidence: list[str] = Field(default_factory=list)
    severity: str = "medium"


class GapAnalysis(BaseModel):
    topic: str
    gaps: list[ResearchGap]
    summary: str
    paper_ids_analyzed: list[str] = Field(default_factory=list)


class ResearchDirection(BaseModel):
    title: str
    rationale: str
    related_gaps: list[str] = Field(default_factory=list)
    feasibility: str = "medium"


class NoveltyReport(BaseModel):
    topic: str
    directions: list[ResearchDirection]
    disclaimer: str = (
        "These directions are proposed based on identified gaps and do not "
        "constitute claims of original novelty."
    )
