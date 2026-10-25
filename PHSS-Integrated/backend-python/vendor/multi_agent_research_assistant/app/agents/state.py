"""
Shared state definition for LangGraph research workflow.
Uses TypedDict for zero-overhead state management (recommended by LangGraph).
"""
from typing import TypedDict, List, Dict, Any, Literal


class ConversationMessage(TypedDict, total=False):
    """Serializable conversation message."""
    role: Literal["user", "assistant", "system"]
    content: str


class ResearchState(TypedDict, total=False):
    """
    LangGraph state schema.
    
    """
    # Required input fields
    query: str
    thread_id: str
    selected_model: str
    api_key: str
    
    # Classification outputs
    intent: Literal["CHAT", "RESEARCH"]
    requires_academic: bool
    requires_web: bool
    
    # Planning
    plan: List[Dict[str, str]]  # [{"query": "...", "type": "web"}, ...]
    
    # Research results
    web_results: List[Dict[str, Any]]
    academic_results: List[Dict[str, Any]]
    all_sources: List[Dict[str, Any]]
    
    # Final outputs
    final_report: str
    citations: List[Dict[str, str]]
    
    # Human-in-the-loop
    user_feedback: str
    revision_count: int
    approved: bool

    # Chat history (for context)
    messages: List[ConversationMessage]

    # Tracking
    start_time: float
    end_time: float
    current_step: str
    error: str
