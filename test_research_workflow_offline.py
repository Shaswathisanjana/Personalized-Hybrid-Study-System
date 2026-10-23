from app.research_agent.models import ResearchPaper
from app.research_agent.paper_summarizer import (
    PaperSummary,
    NOT_REPORTED,
)
from app.research_agent.research_workflow import (
    IntegratedResearchWorkflow,
)


class MockSummarizer:

    def summarize_multiple(self, papers):

        summaries = []

        for paper in papers:

            if paper.title == "Synthetic CNN Study":

                summaries.append(
                    PaperSummary(
                        title=paper.title,
                        authors=paper.authors,
                        year=paper.year,
                        source_url=paper.url,
                        proposed_method="CNN classification.",
                        dataset="1000 labelled images.",
                        limitations=(
                            "Evaluation used data from "
                            "only one institution."
                        ),
                        evidence_quotes={
                            "proposed_method": "CNN classification.",
                            "dataset": "1000 labelled images.",
                            "limitations": (
                                "Evaluation used data from "
                                "only one institution."
                            ),
                        },
                    )
                )

            else:

                summaries.append(
                    PaperSummary(
                        title=paper.title,
                        authors=paper.authors,
                        year=paper.year,
                        source_url=paper.url,
                        proposed_method="Transformer classification.",
                        dataset="2000 labelled images.",
                        limitations=NOT_REPORTED,
                        evidence_quotes={
                            "proposed_method": (
                                "Transformer classification."
                            ),
                            "dataset": "2000 labelled images.",
                        },
                    )
                )

        return summaries


class MockFailingThematicReviewer:

    def review(self, topic, summaries):
        raise RuntimeError("Simulated temporary API failure")


def main():

    print("\nSTEP 1: Creating synthetic papers...")

    papers = [
        ResearchPaper(
            title="Synthetic CNN Study",
            authors=["Test Author A"],
            abstract=(
                "This synthetic study investigates automated "
                "medical image classification using deep learning. "
                "CNN classification. "
                "The experimental dataset contains "
                "1000 labelled images. "
                "The study examines how image-based features "
                "can support diagnostic classification and "
                "compares predictions against reference labels. "
                "Evaluation used data from only one institution. "
                "This restricted evaluation setting limits "
                "the conclusions that can be drawn about "
                "generalization to other institutions."
            ),
            url="https://example.org/synthetic-a",
            year=2024,
        ),
        ResearchPaper(
            title="Synthetic Transformer Study",
            authors=["Test Author B"],
            abstract=(
                "This synthetic research paper investigates "
                "deep learning approaches for classifying "
                "medical images into diagnostic categories. "
                "Transformer classification. "
                "The experimental dataset contains "
                "2000 labelled images. "
                "The study explores attention-based image "
                "representations and examines their usefulness "
                "for automated classification. "
                "Predictions are compared against labelled "
                "reference examples to study the proposed "
                "approach in a controlled experimental setting."
            ),
            url="https://example.org/synthetic-b",
            year=2025,
        ),
    ]

    print("\nSTEP 2: Running integrated workflow...")

    workflow = IntegratedResearchWorkflow(
        summarizer=MockSummarizer(),
        thematic_reviewer=MockFailingThematicReviewer(),
    )

    result = workflow.run(
        topic="Medical Image Classification",
        papers=papers,
        include_thematic_review=True,
    )

    print("\n========== WORKFLOW RESULTS ==========")

    print("Papers:", len(result.papers))
    print("Summaries:", len(result.summaries))

    print(
        "Comparison available:",
        result.comparison is not None,
    )

    print(
        "Research opportunities:",
        len(result.gap_report.candidates),
    )

    print(
        "Proposed objectives:",
        len(result.proposal.directions),
    )

    print("Warnings:", result.warnings)

    print("\n========== VALIDATION ==========")

    assert len(result.papers) == 2
    assert len(result.summaries) == 2

    assert result.comparison is not None
    assert len(result.comparison.papers) == 2

    assert result.gap_report is not None
    assert len(result.gap_report.candidates) == 1

    assert result.proposal is not None
    assert len(result.proposal.directions) == 1

    assert result.thematic_review is None

    assert any(
        "Simulated temporary API failure" in warning
        for warning in result.warnings
    )

    print("Both papers processed correctly.")
    print("Methodology comparison generated.")
    print("Supported research opportunity identified.")
    print("Preliminary research objective generated.")
    print("Thematic review failure handled gracefully.")

    print(
        "\nTEST PASSED: Integrated Research Workflow "
        "works correctly."
    )


if __name__ == "__main__":
    main()
