from app.research_agent.paper_summarizer import (
    PaperSummary,
    NOT_REPORTED,
)
from app.research_agent.methodology_comparator import (
    MethodologyComparator,
)


def main():

    print("\nSTEP 1: Creating synthetic research summaries...")

    paper1 = PaperSummary(
        title="Synthetic CNN Study",
        authors=["Test Author A"],
        year=2024,
        source_url="https://example.org/synthetic-a",
        proposed_method="Convolutional neural network.",
        dataset="1000 labelled medical images.",
        evaluation_metrics="Accuracy and F1-score.",
        key_findings="The model achieved 85 percent accuracy.",
        evidence_quotes={
            "proposed_method": "Convolutional neural network.",
            "dataset": "1000 labelled medical images.",
            "evaluation_metrics": "Accuracy and F1-score.",
            "key_findings": "The model achieved 85 percent accuracy.",
        },
    )

    paper2 = PaperSummary(
        title="Synthetic Transformer Study",
        authors=["Test Author B"],
        year=2025,
        source_url="https://example.org/synthetic-b",
        proposed_method="Transformer-based classification.",
        dataset="2000 labelled medical images.",
        limitations="Evaluation was limited to one institution.",
        evidence_quotes={
            "proposed_method": "Transformer-based classification.",
            "dataset": "2000 labelled medical images.",
            "limitations": "Evaluation was limited to one institution.",
        },
    )

    print("Prepared 2 synthetic papers.")

    print("\nSTEP 2: Generating methodology comparison...")

    comparator = MethodologyComparator()

    comparison = comparator.compare(
        topic="Medical Image Classification",
        summaries=[paper1, paper2],
    )

    print("\n========== COMPARISON TABLE ==========\n")

    markdown = comparator.to_markdown(comparison)

    print(markdown)

    print("\n========== VALIDATION ==========")

    assert len(comparison.papers) == 2

    first = comparison.papers[0]
    second = comparison.papers[1]

    assert first.fields["dataset"].is_supported
    assert second.fields["dataset"].is_supported

    assert first.fields["key_findings"].is_supported

    assert (
        second.fields["key_findings"].value
        == NOT_REPORTED
    )

    assert not second.fields["key_findings"].is_supported

    assert (
        first.fields["limitations"].value
        == NOT_REPORTED
    )

    assert not first.fields["limitations"].is_supported

    assert (
        first.fields["proposed_method"].source_quote
        == "Convolutional neural network."
    )

    assert "Synthetic CNN Study" in markdown
    assert "Synthetic Transformer Study" in markdown
    assert "Not reported in available source" in markdown

    print("Papers compared: 2")
    print("Missing information handled correctly.")
    print("Supporting evidence preserved.")
    print("\nTEST PASSED: Methodology comparison works correctly.")


if __name__ == "__main__":
    main()
