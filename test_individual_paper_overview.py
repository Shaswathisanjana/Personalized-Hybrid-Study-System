from app.research_agent.paper_summarizer import (
    PaperSummary,
    NOT_REPORTED,
)

from app.research_agent.individual_paper_overview import (
    IndividualPaperOverviewBuilder,
)


def main():

    print("\nSTEP 1: Creating synthetic paper summaries...")

    paper1 = PaperSummary(
        title="Synthetic CNN Research",
        authors=["Researcher A"],
        year=2024,
        source_url="https://example.org/paper1",
        research_problem="Medical image classification",
        proposed_method="A CNN-based classification model",
        dataset="1000 labelled medical images",
        evaluation_metrics="Accuracy and precision",
        key_findings="The model classified the test images",
        limitations="Data came from one institution",
        evidence_quotes={
            "research_problem": "Medical image classification",
            "proposed_method": "A CNN-based classification model",
            "dataset": "1000 labelled medical images",
            "evaluation_metrics": "Accuracy and precision",
            "key_findings": "The model classified the test images",
            "limitations": "Data came from one institution",
        },
    )

    paper2 = PaperSummary(
        title="Synthetic Transformer Research",
        authors=["Researcher B"],
        year=2025,
        source_url="https://example.org/paper2",
        research_problem=NOT_REPORTED,
        proposed_method="A transformer-based model",
        dataset=NOT_REPORTED,
        evaluation_metrics=NOT_REPORTED,
        key_findings=NOT_REPORTED,
        limitations=NOT_REPORTED,
        evidence_quotes={
            "proposed_method": "A transformer-based model",
        },
    )

    paper3 = PaperSummary(
        title="Insufficient Abstract Example",
        authors=["Researcher C"],
        year=2023,
        source_url="https://example.org/paper3",
        research_problem=NOT_REPORTED,
        proposed_method=NOT_REPORTED,
        dataset=NOT_REPORTED,
        evaluation_metrics=NOT_REPORTED,
        key_findings=NOT_REPORTED,
        limitations=NOT_REPORTED,
        evidence_quotes={},
    )

    print("\nSTEP 2: Generating individual overviews...")

    overviews = IndividualPaperOverviewBuilder.build_multiple(
        [paper1, paper2, paper3]
    )

    assert len(overviews) == 3

    print("\n========== PAPER 1 ==========")
    print(overviews[0].simple_summary)

    print("\n========== PAPER 2 ==========")
    print(overviews[1].simple_summary)

    print("\n========== PAPER 3 ==========")
    print(overviews[2].simple_summary)

    print("\nSTEP 3: Validating the results...")

    assert "CNN-based classification model" in (
        overviews[0].simple_summary
    )

    assert "1000 labelled medical images" in (
        overviews[0].simple_summary
    )

    assert "transformer-based model" in (
        overviews[1].simple_summary
    )

    assert NOT_REPORTED not in (
        overviews[1].simple_summary
    )

    assert "not contain enough verified information" in (
        overviews[2].simple_summary
    )

    assert overviews[0].source_url == (
        "https://example.org/paper1"
    )

    assert overviews[1].source_url == (
        "https://example.org/paper2"
    )

    assert overviews[2].evidence_scope == "abstract_only"

    print("\nAll individual overview checks passed.")

    print(
        "\nTEST PASSED: Individual Paper Overview "
        "module works correctly."
    )


if __name__ == "__main__":
    main()
