from __future__ import annotations
import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from app.core.state import AgentState
from app.core.llm import get_llm
from app.core.router import INTENT_TO_PIPELINE

logger = logging.getLogger(__name__)

_PROMPT = ChatPromptTemplate.from_messages([
    ("human", """You are the orchestrator for a multi-agent research assistant.
Classify the user's query into EXACTLY one of these intents:
  search_only | read_paper | lit_review | gap_analysis | novelty | full_report | qa

Also extract the core research topic (not the full sentence).

Return ONLY valid JSON — no explanation, no markdown:
{{"intent": "<intent>", "topic": "<core topic>"}}

User query: {query}"""),
])


async def manager_node(state: AgentState) -> dict:
    """Intent classification and pipeline planning."""
    llm   = get_llm(temperature=0)
    chain = _PROMPT | llm
    result = await chain.ainvoke({"query": state["user_query"]})

    raw = result.content.strip()
    # Strip markdown fences Gemini sometimes adds
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"Manager: JSON parse failed on: {raw!r}, defaulting to full_report")
        parsed = {"intent": "full_report", "topic": state["user_query"]}

    intent   = parsed.get("intent", "full_report")
    topic    = parsed.get("topic", state["user_query"])
    pipeline = INTENT_TO_PIPELINE.get(intent, INTENT_TO_PIPELINE["full_report"])

    logger.info(f"Manager: intent={intent!r}, topic={topic!r}")
    return {
        "intent":       intent,
        "topic":        topic,
        "pipeline":     pipeline,
        "current_step": pipeline[0],
        "retry_count":  0,
        "errors":       [],
    }


async def error_node(state: AgentState) -> dict:
    retry = state.get("retry_count", 0) + 1
    logger.error(f"Error recovery attempt {retry}. Errors: {state.get('errors')}")
    return {"retry_count": retry}
