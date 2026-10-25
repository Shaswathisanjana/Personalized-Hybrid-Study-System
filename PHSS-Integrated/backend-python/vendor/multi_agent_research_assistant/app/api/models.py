"""Pydantic models for request/response validation."""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    """Serializable message payload from the frontend."""
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1, max_length=2000)

class ResearchRequest(BaseModel):
    """Request model for initiating research."""
    query: str = Field(
        ..., 
        min_length=1, 
        max_length=1500, 
        description="Research question or topic"
    )
    thread_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    user_feedback: Optional[str] = Field(None, description="Feedback for report revision")
    model: Optional[str] = Field(None, description="Optional OpenRouter model override for this request")
    api_key: Optional[str] = Field(None, description="Optional user-provided OpenRouter API key")
    messages: List[ConversationMessage] = Field(default_factory=list, description="Recent conversation history for stateless context")


class FeedbackRequest(BaseModel):
    """Feedback model for human review flow."""
    feedback: str = Field(default="", max_length=2000)
    approved: bool = False


class ResearchResponse(BaseModel):
    """Response model for research results."""
    thread_id: str
    status: str
    report: Optional[str] = None
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    execution_time: Optional[float] = None
    estimated_cost: Optional[float] = None


class SystemStats(BaseModel):
    """System metrics for admin dashboard."""
    total_queries: int
    successful_queries: int
    failed_queries: int
    avg_latency: float
    total_cost: float
    active_users: int
    queries_today: int

class HealthCheck(BaseModel):
    """API health status."""
    status: str
    version: str
    uptime: float
    database: str
    llm_service: str
    timestamp: datetime