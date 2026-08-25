from __future__ import annotations
import json
import uuid
import logging
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate

from app.core.state import AgentState
from app.core.llm import get_llm
from app.models.report import ResearchReport
from app.export import export_all

logger = logging.getLogger(__name__)

_PROMPT = ChatPromptTemplate.from_messages([
    ("human", """You are a professional academic report writer.
Write formally in third person. Synthesise all inputs — do not paste them verbatim.
Return ONLY valid JSON — no markdown fences.

Topic: {topic}

Literature Review:
{lr_json}

Gap Analysis:
{gap_json}

Novelty Report:
{novelty_json}

Papers Used:
{paper_list}

Generate a full research report. Return JSON with these exact keys:
{{
  "title": "Full report title",
  "abstract": "250-300 word abstract",
  "introduction": "600-800 word introduction",
  "literature_review": "Synthesised literature review text",
  "comparative_analysis": "800-1000 word comparative analysis of methods, datasets, results",
  "research_gaps": "500-700 word section on identified gaps",
  "future_directions": "500-700 word section on proposed research directions"
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


async def writing_node(state: AgentState) -> dict:
    topic   = state["topic"]
    papers  = state.get("papers", [])
    lr      = state.get("literature_review") or {}
    gap     = state.get("gap_analysis") or {}
    novelty = state.get("novelty_report") or {}

    paper_list = "\n".join(
        f"- {p.get('title', p) if isinstance(p, dict) else p.title} "
        f"({p.get('year', '') if isinstance(p, dict) else p.year}) "
        f"— {p.get('paper_id', '') if isinstance(p, dict) else p.paper_id}"
        for p in papers[:25]
    )

    llm   = get_llm(temperature=0.3)
    chain = _PROMPT | llm
    result = await chain.ainvoke({
        "topic":        topic,
        "lr_json":      json.dumps(lr)[:3500],
        "gap_json":     json.dumps(gap)[:3500],
        "novelty_json": json.dumps(novelty)[:2500],
        "paper_list":   paper_list[:1500],
    })
    raw = _strip_fences(result.content)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Writing: JSON parse failed, using empty sections")
        data = {}

    report_id = f"report_{uuid.uuid4().hex[:8]}"
    report = ResearchReport(
        report_id=report_id,
        topic=topic,
        generated_at=datetime.utcnow(),
        title=data.get("title", f"Research Report: {topic}"),
        abstract=data.get("abstract", ""),
        introduction=data.get("introduction", ""),
        literature_review=data.get("literature_review", ""),
        comparative_analysis=data.get("comparative_analysis", ""),
        research_gaps=data.get("research_gaps", ""),
        future_directions=data.get("future_directions", ""),
        paper_ids=[
            (p.get("paper_id") if isinstance(p, dict) else p.paper_id)
            for p in papers
        ],
    )

    # Export to MD / DOCX / PDF
    report = export_all(report)

    pipeline  = state.get("pipeline", [])
    idx       = pipeline.index("writing_node") if "writing_node" in pipeline else -1
    next_step = pipeline[idx + 1] if idx + 1 < len(pipeline) else "END"

    return {"report": report.model_dump(), "current_step": next_step}
