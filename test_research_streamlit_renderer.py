from streamlit.testing.v1 import AppTest

from app.research_agent.models import ResearchPaper
from app.research_agent.research_workflow import IntegratedResearchWorkflow
from app.research_agent.report_exporter import ResearchReportExporter

from test_research_workflow_offline import MockSummarizer


def main():

    print("\nSTEP 1: Starting offline Streamlit test...")

    app = AppTest.from_file(
        "test_research_streamlit_app.py",
        default_timeout=30,
    )

    app.run()

    if len(app.exception) > 0:
        for error in app.exception:
            print(error.message)

        raise AssertionError(
            "Advanced Research Renderer raised an exception."
        )

    print("Streamlit renderer executed without exceptions.")

    print("\nSTEP 2: Checking individual paper sections...")

    paper_expanders = [
        item
        for item in app.get("expander")
        if item.label.startswith("Paper ")
    ]

    assert len(paper_expanders) == 2, (
        f"Expected 2 individual paper expanders, "
        f"found {len(paper_expanders)}."
    )

    print("Individual paper sections:", len(paper_expanders))

    print("\nSTEP 3: Checking report generation...")

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

    workflow = IntegratedResearchWorkflow(
        summarizer=MockSummarizer(),
    )

    result = workflow.run(
        topic="Synthetic Medical Image Classification",
        papers=papers,
        include_thematic_review=False,
    )

    report = ResearchReportExporter().build_markdown(result)

    assert isinstance(report, str)
    assert len(report.strip()) > 0

    assert "Synthetic CNN Study" in report
    assert "Synthetic Transformer Study" in report

    assert "Simple Summary" in report
    assert "Detailed Structured Summary" in report

    print("Report generated successfully.")
    print("Report length:", len(report), "characters")

    print(
        "\nTEST PASSED: Advanced Research Results "
        "Renderer and report generation work correctly."
    )


if __name__ == "__main__":
    main()
