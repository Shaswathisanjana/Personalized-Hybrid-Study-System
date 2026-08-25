from __future__ import annotations
import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.core.state import AgentState
from app.core.llm import get_llm
from app.knowledge_base.chroma_client import KnowledgeBase
from app.models.review import GapAnalysis, ResearchGap

logger = logging.getLogger(__name__)
_kb = KnowledgeBase()

_PROMPT = ChatPromptTemplate.from_messages([
    ("human", """You are a critical research analyst. Identify ONLY evidence-based gaps.
Cite paper IDs for every gap. Be specific — avoid vague statements.
Return ONLY valid JSON — no markdown fences.

Topic: {topic}

All Paper Extractions:
{extractions_json}

Identify gaps across these categories:
missing_research | dataset_gap | methodological_gap | evaluation_gap | deployment_gap | reproducibility_gap

Return JSON:
{{
  "gaps": [
    {{
      "gap_type": "<category>",
      "description": "Specific, actionable gap description",
      "evidence": ["paper_id_1", "paper_id_2"],
      "severity": "low|medium|high"
    }}
  ],
  "summary": "2-3 sentence overall summary of the gap landscape"
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


async def gap_node(state: AgentState) -> dict:
    topic     = state["topic"]
    report_id = (state.get("report") or {}).get("report_id", "session_default")

    extractions = _kb.get_all_extractions(report_id) or state.get("extractions", [])
    exts_json   = json.dumps(
        [e.model_dump(exclude={"chroma_doc_id"}) for e in extractions], indent=2
    )

    llm   = get_llm(temperature=0.1)
    chain = _PROMPT | llm
    result = await chain.ainvoke({"topic": topic, "extractions_json": exts_json[:12000]})
    raw = _strip_fences(result.content)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Gap: JSON parse failed")
        data = {"gaps": [], "summary": "Gap analysis unavailable."}

    gap_analysis = GapAnalysis(
        topic=topic,
        gaps=[ResearchGap(**g) for g in data.get("gaps", [])],
        summary=data.get("summary", ""),
        paper_ids_analyzed=[e.paper_id for e in extractions],
    )

    pipeline  = state.get("pipeline", [])
    idx       = pipeline.index("gap_node") if "gap_node" in pipeline else -1
    next_step = pipeline[idx + 1] if idx + 1 < len(pipeline) else "END"

    return {"gap_analysis": gap_analysis.model_dump(), "current_step": next_step}
