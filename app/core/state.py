from __future__ import annotations
from typing import Optional, Annotated
from typing_extensions import TypedDict
import operator


class AgentState(TypedDict):
    # Input
    user_query: str
    topic: str
    intent: str
    pipeline: list[str]

    # Search Agent outputs
    papers: Annotated[list, operator.add]

    # Reading Agent outputs
    extractions: Annotated[list, operator.add]

    # Review pipeline
    literature_review: Optional[dict]
    gap_analysis: Optional[dict]
    novelty_report: Optional[dict]

    # Writing & Citation
    report: Optional[dict]
    citations: Optional[dict]

    # Q&A
    qa_request: Optional[dict]
    qa_response: Optional[dict]

    # Control flow
    errors: Annotated[list[str], operator.add]
    current_step: str
    retry_count: int
