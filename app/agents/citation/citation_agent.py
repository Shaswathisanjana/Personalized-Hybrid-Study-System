from __future__ import annotations
import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.core.state import AgentState
from app.core.llm import get_llm
from app.models.report import FormattedCitations

logger = logging.getLogger(__name__)

_IEEE_PROMPT = ChatPromptTemplate.from_messages([
    ("human", """Format these papers in IEEE citation style.
Use only the provided metadata — do not invent DOIs or page numbers.
Return ONLY valid JSON: {{"ieee": ["[1] Author, Title...", "[2] ..."]}}

Papers:
{papers_json}"""),
])


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text.split("\n", 1)[1] if "\n" in text else text[4:]
    return text.strip()


def _parse_list(raw: str, key: str) -> list[str]:
    raw = _strip_fences(raw)
    try:
        return json.loads(raw).get(key, [])
    except Exception:
        return []


async def citation_node(state: AgentState) -> dict:
    papers = state.get("papers", [])
    papers_json = json.dumps([
        {
            "paper_id": p.get("paper_id") if isinstance(p, dict) else p.paper_id,
            "title":    p.get("title")    if isinstance(p, dict) else p.title,
            "authors":  p.get("authors")  if isinstance(p, dict) else p.authors,
            "year":     p.get("year")     if isinstance(p, dict) else p.year,
            "doi":      p.get("doi")      if isinstance(p, dict) else p.doi,
            "venue":    p.get("venue")    if isinstance(p, dict) else p.venue,
        }
        for p in papers
    ], indent=2)[:8000]

    llm = get_llm(temperature=0)
    ieee_r = await (_IEEE_PROMPT | llm).ainvoke({"papers_json": papers_json})

    cites = FormattedCitations(
        ieee=_parse_list(ieee_r.content, "ieee"),
        apa=[],
        bibtex="",
    )

    report = state.get("report") or {}
    report["citations"] = cites.model_dump()

    pipeline  = state.get("pipeline", [])
    idx       = pipeline.index("citation_node") if "citation_node" in pipeline else -1
    next_step = pipeline[idx + 1] if idx + 1 < len(pipeline) else "END"

    return {"citations": cites.model_dump(), "report": report, "current_step": next_step}
