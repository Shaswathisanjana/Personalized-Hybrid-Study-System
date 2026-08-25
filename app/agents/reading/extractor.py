from __future__ import annotations
import json
import re
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.models.paper import PaperMetadata, PaperExtraction
from app.core.llm import get_llm

logger = logging.getLogger(__name__)

_PROMPT = ChatPromptTemplate.from_messages([
    ("human", """You are a research paper analyst. Extract structured information precisely.
Use ONLY what is explicitly stated in the text. Return null for missing fields.
Return ONLY valid JSON — no markdown fences, no explanation.

Paper: {title}
Authors: {authors} ({year})

Text:
\"\"\"{text}\"\"\"

Extract and return JSON with these exact keys:
{{
  "problem_statement": "The core problem this paper addresses",
  "objective": "What this paper aims to achieve",
  "datasets_used": ["list of dataset names"],
  "methodology": "The method or approach proposed",
  "model_architecture": "Model/system architecture details",
  "results_summary": "Key quantitative and qualitative results",
  "evaluation_metrics": ["list of metrics used"],
  "limitations": "Explicitly stated limitations",
  "future_work": "Suggested future work from the paper",
  "keywords": ["5 to 10 keywords"]
}}"""),
])


def _strip_fences(text: str) -> str:
    """Remove markdown code fences that Gemini sometimes adds."""
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


async def extract_structured_info(
    paper: PaperMetadata, text: str
) -> PaperExtraction:
    llm   = get_llm(temperature=0.1)
    chain = _PROMPT | llm
    result = await chain.ainvoke({
        "title":   paper.title,
        "authors": ", ".join(paper.authors[:5]),
        "year":    paper.year or "unknown",
        "text":    text[:10000],  # token budget guard
    })

    raw = _strip_fences(result.content)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"Extractor: JSON parse failed for {paper.paper_id}")
        data = {}

    return PaperExtraction(
        paper_id=paper.paper_id,
        title=paper.title,
        authors=paper.authors,
        year=paper.year,
        doi=paper.doi,
        problem_statement=data.get("problem_statement"),
        objective=data.get("objective"),
        datasets_used=data.get("datasets_used") or [],
        methodology=data.get("methodology"),
        model_architecture=data.get("model_architecture"),
        results_summary=data.get("results_summary"),
        evaluation_metrics=data.get("evaluation_metrics") or [],
        limitations=data.get("limitations"),
        future_work=data.get("future_work"),
        keywords=data.get("keywords") or paper.keywords,
    )
