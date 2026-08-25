from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class FormattedCitations(BaseModel):
    ieee: list[str]
    apa: list[str]
    bibtex: str


class ResearchReport(BaseModel):
    report_id: str
    topic: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    title: str
    abstract: str
    introduction: str
    literature_review: str
    comparative_analysis: str
    research_gaps: str
    future_directions: str

    citations: Optional[FormattedCitations] = None
    paper_ids: list[str] = Field(default_factory=list)

    markdown_path: Optional[str] = None
    docx_path: Optional[str] = None
    pdf_path: Optional[str] = None

    @property
    def full_markdown(self) -> str:
        parts = [
            f"# {self.title}\n",
            f"**Generated:** {self.generated_at.strftime('%Y-%m-%d')}",
            f"## Abstract\n{self.abstract}",
            f"## 1. Introduction\n{self.introduction}",
            f"## 2. Literature Review\n{self.literature_review}",
            f"## 3. Comparative Analysis\n{self.comparative_analysis}",
            f"## 4. Research Gaps\n{self.research_gaps}",
            f"## 5. Future Directions\n{self.future_directions}",
        ]
        if self.citations:
            ref_section = "\n".join(
                f"[{i+1}] {ref}" for i, ref in enumerate(self.citations.ieee)
            )
            parts.append(f"## References\n{ref_section}")
        return "\n\n---\n\n".join(parts)
