import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from agentic_controller import AgenticResearchController


def test_plan_has_bounded_search_budget():
    controller = AgenticResearchController(max_adaptive_searches=1)
    plan = controller.create_plan("PCB defect detection", 5)
    assert plan["adaptive_search_budget"] == 1
    assert len(plan["evidence_targets"]) >= 3


def test_retrieval_evaluation_detects_shortfall():
    controller = AgenticResearchController()
    result = controller.evaluate_retrieval(
        "PCB defect detection",
        [{"title": "PCB defect detection with CNN", "abstract": "Detection of PCB defects", "relevance_score": 0.7}],
        5,
    )
    assert result["needs_adaptation"] is True
    assert result["paper_count"] == 1


def test_merge_unique_uses_url_and_title():
    controller = AgenticResearchController()
    merged = controller.merge_unique(
        [{"title": "Paper A", "url": "https://example.org/a"}],
        [{"title": "Paper A duplicate", "url": "https://example.org/a"}, {"title": "Paper B", "url": "https://example.org/b"}],
    )
    assert len(merged) == 2


def test_missing_fields_are_not_fabricated():
    result = AgenticResearchController.evaluate_extraction([
        {"methodology": "CNN", "dataset": "Not explicitly reported in full text", "results_metrics": "95%", "author_stated_limitations": "Not explicitly reported in full text", "future_work": "Future work is suggested"}
    ])
    assert result["field_status"]["dataset"]["missing"] == 1
    assert result["field_status"]["author_stated_limitations"]["missing"] == 1
    assert result["decision"] == "proceed_with_caveats"


def test_full_count_but_low_relevance_triggers_adaptation():
    controller = AgenticResearchController(
        min_relevance_score=0.30,
        min_relevant_ratio=0.60,
    )
    papers = [
        {"title": f"Paper {i}", "abstract": "PCB defect detection", "relevance_score": 0.15}
        for i in range(5)
    ]
    result = controller.evaluate_retrieval("PCB defect detection", papers, 5)
    assert result["paper_count"] == 5
    assert result["relevant_paper_ratio"] == 0.0
    assert result["needs_adaptation"] is True
    assert len(result["low_relevance_papers"]) == 5
