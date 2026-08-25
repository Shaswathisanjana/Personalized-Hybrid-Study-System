from __future__ import annotations
import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.core.state import AgentState
from app.core.llm import get_llm
from app.models.review import NoveltyReport, ResearchDirection

logger = logging.getLogger(__name__)

_PROMPT = ChatPromptTemplate.from_messages([
    ("human", """You are a creative research strategist. Propose future research directions
grounded in the identified gaps. Frame proposals as possibilities, not certainties.
Never claim novelty. Return ONLY valid JSON — no markdown fences.

Topic: {topic}

Research Gaps:
{gaps_json}

Propose 4-7 directions. Return JSON:
{{
  "directions": [
    {{
      "title": "Short descriptive title",
      "rationale": "Why this direction is worth exploring, grounded in the gaps",
      "related_gaps": ["gap_type"],
      "feasibility": "low|medium|high"
    }}
  ]
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


async def novelty_node(state: AgentState) -> dict:
    topic        = state["topic"]
    gap_analysis = state.get("gap_analysis") or {}
    gaps_json    = json.dumps(gap_analysis.get("gaps", []), indent=2)

    llm   = get_llm(temperature=0.4)
    chain = _PROMPT | llm
    result = await chain.ainvoke({"topic": topic, "gaps_json": gaps_json[:6000]})
    raw = _strip_fences(result.content)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Novelty: JSON parse failed")
        data = {"directions": []}

    report = NoveltyReport(
        topic=topic,
        directions=[ResearchDirection(**d) for d in data.get("directions", [])],
    )

    pipeline  = state.get("pipeline", [])
    idx       = pipeline.index("novelty_node") if "novelty_node" in pipeline else -1
    next_step = pipeline[idx + 1] if idx + 1 < len(pipeline) else "END"

    return {"novelty_report": report.model_dump(), "current_step": next_step}
