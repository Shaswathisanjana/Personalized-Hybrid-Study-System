from __future__ import annotations
import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.core.state import AgentState
from app.core.llm import get_llm
from app.knowledge_base.chroma_client import KnowledgeBase
from app.models.review import (
    LiteratureReview, MethodComparison,
    GapAnalysis, ResearchGap,
    NoveltyReport, ResearchDirection,
)

logger = logging.getLogger(__name__)
_kb = KnowledgeBase()

_PROMPT = ChatPromptTemplate.from_messages([
    ("human", """You are a senior research analyst. Given a topic and a set of paper extractions,
produce THREE outputs in a single JSON response. Be thorough and evidence-based.
Return ONLY valid JSON — no markdown fences, no explanation.

Topic: {topic}

Paper Extractions:
{extractions_json}

Return JSON with EXACTLY these top-level keys:

{{
  "literature_review": {{
    "introduction": "2-3 paragraphs introducing the topic and scope",
    "existing_approaches": "Overview of the main categories of approaches found in the papers",
    "method_comparison": [
      {{"aspect": "comparison dimension", "papers": {{"paper_id": "brief description"}}}}
    ],
    "trends": "Observed trends and shifts over time across the papers",
    "strengths_and_weaknesses": "Cross-paper strengths and weaknesses",
    "chronological_developments": "How the field evolved chronologically"
  }},

  "gap_analysis": {{
    "gaps": [
      {{
        "gap_type": "missing_research|dataset_gap|methodological_gap|evaluation_gap|deployment_gap|reproducibility_gap",
        "description": "Specific, actionable gap description grounded in the papers",
        "evidence": ["paper_id_1", "paper_id_2"],
        "severity": "low|medium|high"
      }}
    ],
    "summary": "2-3 sentence overall summary of the gap landscape"
  }},

  "novelty_report": {{
    "directions": [
      {{
        "title": "Short descriptive title for the research direction",
        "rationale": "Why this direction is worth exploring, grounded in the gaps",
        "related_gaps": ["gap_type"],
        "feasibility": "low|medium|high"
      }}
    ]
  }}
}}"""),
])


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text.split("\n", 1)[1] if "\n" in text else text[4:]
    return text.strip()


async def analysis_node(state: AgentState) -> dict:
    """Combined lit-review + gap-detection + novelty in a single LLM call."""
    topic     = state["topic"]
    report_id = (state.get("report") or {}).get("report_id", "session_default")

    # Prefer KB extractions; fall back to state
    db_exts  = _kb.get_all_extractions(report_id)
    all_exts = db_exts if db_exts else state.get("extractions", [])

    exts_json = json.dumps(
        [e.model_dump(exclude={"chroma_doc_id"}) for e in all_exts], indent=2
    )[:14000]  # token budget guard

    llm   = get_llm(temperature=0.3)
    chain = _PROMPT | llm
    result = await chain.ainvoke({"topic": topic, "extractions_json": exts_json})
    raw = _strip_fences(result.content)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Analysis: JSON parse failed — using empty outputs")
        data = {}

    # ── Literature Review ──────────────────────────────────────────────────────
    lr_data = data.get("literature_review") or {}
    review = LiteratureReview(
        topic=topic,
        introduction=lr_data.get("introduction", ""),
        existing_approaches=lr_data.get("existing_approaches", ""),
        method_comparison=[
            MethodComparison(**mc) for mc in lr_data.get("method_comparison", [])
        ],
        trends=lr_data.get("trends", ""),
        strengths_and_weaknesses=lr_data.get("strengths_and_weaknesses", ""),
        chronological_developments=lr_data.get("chronological_developments", ""),
        paper_ids_covered=[e.paper_id for e in all_exts],
    )

    # ── Gap Analysis ───────────────────────────────────────────────────────────
    gap_data = data.get("gap_analysis") or {}
    gap_analysis = GapAnalysis(
        topic=topic,
        gaps=[ResearchGap(**g) for g in gap_data.get("gaps", [])],
        summary=gap_data.get("summary", ""),
        paper_ids_analyzed=[e.paper_id for e in all_exts],
    )

    # ── Novelty Report ─────────────────────────────────────────────────────────
    nov_data = data.get("novelty_report") or {}
    novelty = NoveltyReport(
        topic=topic,
        directions=[ResearchDirection(**d) for d in nov_data.get("directions", [])],
    )

    # ── Advance pipeline ───────────────────────────────────────────────────────
    pipeline  = state.get("pipeline", [])
    idx       = pipeline.index("analysis_node") if "analysis_node" in pipeline else -1
    next_step = pipeline[idx + 1] if idx + 1 < len(pipeline) else "END"

    return {
        "literature_review": review.model_dump(),
        "gap_analysis":      gap_analysis.model_dump(),
        "novelty_report":    novelty.model_dump(),
        "current_step":      next_step,
    }
