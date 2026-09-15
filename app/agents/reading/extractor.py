from __future__ import annotations
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.models.paper import PaperMetadata, PaperExtraction
from app.core.llm import get_llm
from app.core.json_utils import parse_llm_json

logger = logging.getLogger(__name__)

_PROMPT = ChatPromptTemplate.from_messages([
    ("human", """You are a research paper analyst. Extract structured information precisely.
Use ONLY what is explicitly stated in the text. Return "Not Mentioned" for missing string fields,
empty list [] for missing list fields. Return ONLY valid JSON — no markdown fences, no explanation.

Paper: {title}
Authors: {authors} ({year})

Text:
\"\"\"{text}\"\"\"

Extract and return JSON with these exact keys:
{{
  "problem_statement": "The core problem this paper addresses",
  "objective": "What this paper aims to achieve",
  "domain": "Research domain e.g. Computer Vision / Industrial Inspection",
  "datasets_used": ["list of dataset names used"],
  "dataset_size": "Number of images/samples if mentioned else Not Mentioned",
  "methodology": "The method or approach proposed",
  "model_architecture": "Full model/system architecture description",
  "backbone": "Backbone network used e.g. ResNet50 VGG16 or Not Mentioned",
  "loss_function": "Loss function used or Not Mentioned",
  "optimizer": "Optimizer used e.g. Adam SGD or Not Mentioned",
  "epochs": "Number of training epochs or Not Mentioned",
  "batch_size": "Batch size or Not Mentioned",
  "evaluation_metrics": ["list of metrics used e.g. mAP F1 Precision Recall"],
  "accuracy": "Accuracy value with percent if mentioned else Not Mentioned",
  "precision": "Precision value with percent if mentioned else Not Mentioned",
  "recall": "Recall value with percent if mentioned else Not Mentioned",
  "f1_score": "F1 score value with percent if mentioned else Not Mentioned",
  "map_score": "mAP value with percent if mentioned else Not Mentioned",
  "results_summary": "Key quantitative and qualitative results in 2-3 sentences",
  "advantages": ["list of key strengths or advantages of this approach"],
  "limitations": "Explicitly stated limitations or shortcomings",
  "novel_contributions": ["list of novel contributions introduced by this paper"],
  "future_work": "Suggested future work from the paper",
  "keywords": ["5 to 10 keywords"]
}}"""),
])


async def extract_structured_info(
    paper: PaperMetadata, text: str
) -> PaperExtraction:
    try:
        llm   = get_llm(temperature=0.1)
        chain = _PROMPT | llm
        result = await chain.ainvoke({
            "title":   paper.title,
            "authors": ", ".join(paper.authors[:5]),
            "year":    paper.year or "unknown",
            "text":    text[:10000],  # token budget guard
        })
        data = parse_llm_json(result.content, context=f"extractor:{paper.paper_id}")
    except Exception as exc:
        # Rate-limited or other API error — build minimal extraction from metadata
        logger.warning("Extractor: LLM call failed for %s (%s), using metadata fallback", paper.paper_id, exc)
        data = {}

    def _str(key: str) -> str | None:
        v = data.get(key)
        return None if not v or v == "Not Mentioned" else str(v)

    def _lst(key: str) -> list[str]:
        v = data.get(key)
        return [str(i) for i in v] if isinstance(v, list) else []

    return PaperExtraction(
        paper_id=paper.paper_id,
        title=paper.title,
        authors=paper.authors,
        year=paper.year,
        doi=paper.doi,
        # Core fields
        problem_statement=_str("problem_statement") or _first_sentence(text or paper.abstract or ""),
        objective=_str("objective"),
        domain=_str("domain"),
        datasets_used=_lst("datasets_used"),
        dataset_size=_str("dataset_size"),
        methodology=_str("methodology"),
        model_architecture=_str("model_architecture"),
        results_summary=_str("results_summary"),
        evaluation_metrics=_lst("evaluation_metrics"),
        limitations=_str("limitations"),
        future_work=_str("future_work"),
        keywords=_lst("keywords") or paper.keywords,
        # ML-specific fields
        backbone=_str("backbone"),
        loss_function=_str("loss_function"),
        optimizer=_str("optimizer"),
        epochs=_str("epochs"),
        batch_size=_str("batch_size"),
        advantages=_lst("advantages"),
        novel_contributions=_lst("novel_contributions"),
        # Individual metric values
        accuracy=_str("accuracy"),
        precision=_str("precision"),
        recall=_str("recall"),
        f1_score=_str("f1_score"),
        map_score=_str("map_score"),
    )


def _first_sentence(text: str) -> str:
    """Return the first sentence of text as a fallback problem statement."""
    for sep in (". ", ".\n", "\n"):
        idx = text.find(sep)
        if idx > 20:
            return text[:idx + 1].strip()
    return text[:300].strip() or None
