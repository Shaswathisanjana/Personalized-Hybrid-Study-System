"""Unit tests for the Search Agent."""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, patch
from app.agents.search.search_agent import search_node
from app.models.paper import PaperMetadata


MOCK_PAPER = PaperMetadata(
    paper_id="ss_test123",
    title="Test Paper on Federated Learning",
    authors=["Alice Smith", "Bob Jones"],
    year=2023,
    abstract="This paper studies federated learning in healthcare settings.",
    source="semantic_scholar",
)


@pytest.mark.asyncio
async def test_search_node_returns_papers():
    state = {
        "user_query": "federated learning healthcare",
        "topic": "federated learning healthcare",
        "intent": "search_only",
        "pipeline": ["search_node"],
        "papers": [],
        "extractions": [],
        "errors": [],
        "current_step": "search_node",
        "retry_count": 0,
        "literature_review": None,
        "gap_analysis": None,
        "novelty_report": None,
        "report": None,
        "citations": None,
        "qa_request": None,
        "qa_response": None,
    }
    with (
        patch("app.agents.search.search_agent.search_semantic_scholar",
              new=AsyncMock(return_value=[MOCK_PAPER])),
        patch("app.agents.search.search_agent.search_arxiv",
              new=AsyncMock(return_value=[])),
        patch("app.agents.search.search_agent.search_openalex",
              new=AsyncMock(return_value=[])),
    ):
        result = await search_node(state)

    assert len(result["papers"]) == 1
    assert result["papers"][0].paper_id == "ss_test123"


@pytest.mark.asyncio
async def test_search_node_handles_source_failure():
    state = {
        "user_query": "test", "topic": "test", "intent": "search_only",
        "pipeline": ["search_node"], "papers": [], "extractions": [],
        "errors": [], "current_step": "search_node", "retry_count": 0,
        "literature_review": None, "gap_analysis": None, "novelty_report": None,
        "report": None, "citations": None, "qa_request": None, "qa_response": None,
    }
    with (
        patch("app.agents.search.search_agent.search_semantic_scholar",
              new=AsyncMock(side_effect=Exception("API timeout"))),
        patch("app.agents.search.search_agent.search_arxiv",
              new=AsyncMock(return_value=[MOCK_PAPER])),
        patch("app.agents.search.search_agent.search_openalex",
              new=AsyncMock(return_value=[])),
    ):
        result = await search_node(state)

    assert len(result["papers"]) >= 1
    assert len(result["errors"]) >= 1  # Source failure is logged
