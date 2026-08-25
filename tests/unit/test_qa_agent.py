"""Unit tests for the Q&A Agent."""
from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock
from app.agents.qa.qa_agent import qa_node
from app.models.qa import QARequest


@pytest.mark.asyncio
async def test_qa_node_returns_grounded_answer():
    qa_req = QARequest(
        report_id="report_test001",
        question="What datasets are most commonly used?",
        mode="general",
    )
    base_state = {
        "user_query": qa_req.question, "topic": "", "intent": "qa",
        "pipeline": ["qa_node"], "papers": [], "extractions": [],
        "literature_review": None, "gap_analysis": None, "novelty_report": None,
        "report": {"report_id": "report_test001"}, "citations": None,
        "qa_request": qa_req.model_dump(), "qa_response": None,
        "errors": [], "current_step": "qa_node", "retry_count": 0,
    }
    mock_chunks = [
        {
            "text": "The study uses ImageNet-1K and CIFAR-10 as benchmarks.",
            "metadata": {"paper_id": "ss_001", "title": "ViT Paper"},
            "score": 0.92,
        }
    ]

    with (
        patch("app.agents.qa.qa_agent._kb") as mock_kb,
        patch("app.agents.qa.qa_agent._llm") as mock_llm,
    ):
        mock_kb.retrieve_chunks.return_value = mock_chunks
        mock_llm_response = MagicMock()
        mock_llm_response.content = "The most common datasets are ImageNet-1K and CIFAR-10."
        mock_llm.ainvoke = MagicMock(return_value=mock_llm_response)

        # Patch the chain invocation
        with patch("app.agents.qa.qa_agent._PROMPT") as mock_prompt:
            mock_chain = MagicMock()
            mock_chain.ainvoke = MagicMock(return_value=mock_llm_response)
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)

            result = await qa_node(base_state)

    assert result["qa_response"] is not None


@pytest.mark.asyncio
async def test_qa_node_no_context_returns_grounded_false():
    qa_req = QARequest(
        report_id="nonexistent_report",
        question="What is the meaning of life?",
    )
    base_state = {
        "user_query": qa_req.question, "topic": "", "intent": "qa",
        "pipeline": ["qa_node"], "papers": [], "extractions": [],
        "literature_review": None, "gap_analysis": None, "novelty_report": None,
        "report": {"report_id": "nonexistent_report"}, "citations": None,
        "qa_request": qa_req.model_dump(), "qa_response": None,
        "errors": [], "current_step": "qa_node", "retry_count": 0,
    }
    with patch("app.agents.qa.qa_agent._kb") as mock_kb:
        mock_kb.retrieve_chunks.return_value = []
        result = await qa_node(base_state)

    assert result["qa_response"]["grounded"] is False
    assert result["qa_response"]["confidence"] == 0.0
