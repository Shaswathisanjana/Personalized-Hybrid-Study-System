from __future__ import annotations
import json
import uuid
import logging
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate

from app.core.state import AgentState
from app.core.llm import get_llm
from app.core.json_utils import parse_llm_json
from app.models.report import ResearchReport
from app.export import export_all

logger = logging.getLogger(__name__)

_PROMPT = ChatPromptTemplate.from_messages([
    ("human", """You are a professional academic report writer.
Write formally in third person. Be specific — cite paper titles, methods, datasets, and metric values.
Do NOT write vague abstractions. Every claim should reference specific papers or results.
Return ONLY valid JSON — no markdown fences.

Topic: {topic}

Literature Review (includes per-paper analysis with concrete details):
{lr_json}

Gap Analysis:
{gap_json}

Novelty Report:
{novelty_json}

Papers list:
{paper_list}

Generate a full research report. Return JSON with these exact keys:
{{
  "title": "Full descriptive report title",
  "introduction": "600-800 words. Introduce the topic, its significance, the research problem landscape, and what this review covers. Mention the number and type of papers reviewed.",
  "literature_review": "700-900 words. For each paper covered, describe in detail: the method used, the dataset, backbone, key results with actual metric values (accuracy/mAP/F1), and the novel contribution. Organise by approach category. Do NOT be vague.",
  "comparative_analysis": "700-900 words. Compare the papers across: datasets used, model architectures, backbones, loss functions, evaluation metrics, and achieved performance numbers. Identify which approach performs best and why. Use specific numbers.",
  "research_gaps": "500-700 words. Enumerate specific gaps found across the reviewed papers. For each gap, name which papers exhibit it and why it matters.",
  "future_directions": "500-700 words. Propose concrete research directions grounded in the identified gaps. Each direction should reference specific papers it builds upon."
}}"""),
])


def _build_comparison_table(per_paper: list[dict]) -> str:
    """Build a markdown comparison table from per-paper analysis dicts."""
    if not per_paper:
        return ""

    headers = [
        "Title", "Year", "Dataset", "Dataset Size", "Model / Method",
        "Backbone", "Loss Function", "Metrics", "Accuracy", "Precision",
        "Recall", "F1", "mAP", "Advantages", "Limitations", "Novel Contributions"
    ]

    def _cell(v) -> str:
        if isinstance(v, list):
            return "; ".join(str(x) for x in v) if v else "—"
        return str(v) if v and v != "Not Mentioned" else "—"

    rows = []
    for p in per_paper:
        rows.append([
            _cell(p.get("title")),
            _cell(p.get("year")),
            _cell(p.get("datasets")),
            _cell(p.get("dataset_size")),
            _cell(p.get("model")),
            _cell(p.get("backbone")),
            _cell(p.get("loss_function")),
            _cell(p.get("evaluation_metrics")),
            _cell(p.get("accuracy")),
            _cell(p.get("precision")),
            _cell(p.get("recall")),
            _cell(p.get("f1")),
            _cell(p.get("map")),
            _cell(p.get("advantages")),
            _cell(p.get("limitations")),
            _cell(p.get("novel_contributions")),
        ])

    sep = "| " + " | ".join(["---"] * len(headers)) + " |"
    header_row = "| " + " | ".join(headers) + " |"
    data_rows = [
        "| " + " | ".join(row) + " |"
        for row in rows
    ]
    return "\n".join([header_row, sep] + data_rows)


async def writing_node(state: AgentState) -> dict:
    topic   = state["topic"]
    papers  = state.get("papers", [])
    lr      = state.get("literature_review") or {}
    gap     = state.get("gap_analysis") or {}
    novelty = state.get("novelty_report") or {}

    # Build comparison table from per-paper analysis produced by analysis_node
    per_paper = lr.get("per_paper_analysis", [])
    comparison_table = _build_comparison_table(per_paper)

    paper_list = "\n".join(
        f"- {p.get('title', p) if isinstance(p, dict) else p.title} "
        f"({p.get('year', '') if isinstance(p, dict) else p.year}) "
        f"\u2014 {p.get('paper_id', '') if isinstance(p, dict) else p.paper_id}"
        for p in papers[:25]
    )

    llm   = get_llm(temperature=0.3)
    chain = _PROMPT | llm
    try:
        result = await chain.ainvoke({
            "topic":        topic,
            "lr_json":      json.dumps(lr)[:4000],
            "gap_json":     json.dumps(gap)[:3500],
            "novelty_json": json.dumps(novelty)[:2500],
            "paper_list":   paper_list[:1500],
        })
        data = parse_llm_json(result.content, context="writing_node")
        if not data:
            logger.warning("Writing: JSON parse failed — raw output snippet: %r", result.content[:500])
    except Exception as exc:
        err_msg = str(exc)
        if "429" in err_msg or "quota" in err_msg.lower() or "ResourceExhausted" in err_msg:
            friendly = (
                "⚠️ Gemini free tier quota exhausted. "
                "Wait until tomorrow UTC midnight for the quota to reset, then try again."
            )
        else:
            friendly = f"LLM error during writing: {exc}"
        logger.error("Writing: LLM call failed: %s", exc)
        data = {"_error": friendly}

    _err = data.get("_error", "")
    report_id = f"report_{uuid.uuid4().hex[:8]}"
    report = ResearchReport(
        report_id=report_id,
        topic=topic,
        generated_at=datetime.utcnow(),
        title=data.get("title", f"Research Report: {topic}"),
        # abstract intentionally omitted — not included in report body
        introduction=data.get("introduction", "") or _err,
        literature_review=data.get("literature_review", "") or _err,
        paper_comparison_table=comparison_table,
        comparative_analysis=data.get("comparative_analysis", "") or _err,
        research_gaps=data.get("research_gaps", "") or _err,
        future_directions=data.get("future_directions", "") or _err,
        paper_ids=[
            (p.get("paper_id") if isinstance(p, dict) else p.paper_id)
            for p in papers
        ],
    )

    # Export to MD / DOCX / PDF
    try:
        report = export_all(report)
    except Exception as exc:
        logger.error("Writing: export_all failed: %s", exc)
        errors.append(f"⚠️ Export failed: {exc}")

    pipeline  = state.get("pipeline", [])
    idx       = pipeline.index("writing_node") if "writing_node" in pipeline else -1
    next_step = pipeline[idx + 1] if idx + 1 < len(pipeline) else "END"

    errors = [_err] if _err else []
    return {"report": report.model_dump(), "current_step": next_step, "errors": errors}
