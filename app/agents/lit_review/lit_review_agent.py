from __future__ import annotations
import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.core.state import AgentState
from app.core.llm import get_llm
from app.knowledge_base.chroma_client import KnowledgeBase
from app.models.review import LiteratureReview, MethodComparison

logger = logging.getLogger(__name__)
_kb = KnowledgeBase()

_PROMPT = ChatPromptTemplate.from_messages([
    ("human", """You are an expert academic writer specialising in systematic literature reviews.
Write formally. Synthesise — do NOT copy paper text verbatim.
Return ONLY valid JSON — no markdown fences.

Topic: {topic}

Paper Summaries:
{summaries}

Write a literature review. Return JSON with these exact keys:
{{
  "introduction": "2-3 paragraphs introducing the topic",
  "existing_approaches": "Overview of main categories of approaches",
  "method_comparison": [{{"aspect": "comparison dimension", "papers": {{"paper_id": "description"}}}}],
  "trends": "Observed trends and shifts over time",
  "strengths_and_weaknesses": "Cross-paper strengths and weaknesses",
  "chronological_developments": "How the field evolved chronologically"
}}"""),
])


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


async def lit_review_node(state: AgentState) -> dict:
    topic      = state["topic"]
    report_id  = (state.get("report") or {}).get("report_id", "session_default")

    db_exts = _kb.get_all_extractions(report_id)
    all_exts = db_exts if db_exts else state.get("extractions", [])

    summaries = "\n---\n".join(
        f"[{e.paper_id}] {e.title} ({e.year})\n"
        f"Method: {e.methodology}\nResults: {e.results_summary}\n"
        f"Datasets: {', '.join(e.datasets_used)}"
        for e in all_exts
    )

    llm   = get_llm(temperature=0.3)
    chain = _PROMPT | llm
    result = await chain.ainvoke({"topic": topic, "summaries": summaries[:12000]})
    raw = _strip_fences(result.content)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("LitReview: JSON parse failed")
        data = {}

    review = LiteratureReview(
        topic=topic,
        introduction=data.get("introduction", ""),
        existing_approaches=data.get("existing_approaches", ""),
        method_comparison=[
            MethodComparison(**mc) for mc in data.get("method_comparison", [])
        ],
        trends=data.get("trends", ""),
        strengths_and_weaknesses=data.get("strengths_and_weaknesses", ""),
        chronological_developments=data.get("chronological_developments", ""),
        paper_ids_covered=[e.paper_id for e in all_exts],
    )

    pipeline = state.get("pipeline", [])
    idx      = pipeline.index("lit_review_node") if "lit_review_node" in pipeline else -1
    next_step = pipeline[idx + 1] if idx + 1 < len(pipeline) else "END"

    return {"literature_review": review.model_dump(), "current_step": next_step}
