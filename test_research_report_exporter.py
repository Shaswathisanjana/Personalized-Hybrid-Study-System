from pathlib import Path

from test_research_workflow_offline import (
    MockSummarizer,
    MockFailingThematicReviewer,
)

from app.research_agent.models import ResearchPaper
from app.research_agent.research_workflow import (
    IntegratedResearchWorkflow,
)
from app.research_agent.report_exporter import (
    ResearchReportExporter,
)


def main():

    print("\nSTEP 1: Preparing synthetic research papers...")

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

    print("\nSTEP 3: Exporting Markdown report...")

    output_path = (
        "data/research_reports/"
        "synthetic_research_report.md"
    )

    exported_path = ResearchReportExporter.export(
        result=result,
        output_path=output_path,
    )

    print("Report created:", exported_path)

    print("\nSTEP 4: Validating report contents...")

    assert exported_path.exists()

    content = exported_path.read_text(
        encoding="utf-8"
    )

    required_sections = [
        "# Academic Research Analysis Report",
        "## 1. Structured Paper Summaries",
        "## 2. Thematic Literature Review",
        "## 3. Methodology Comparison",
        "## 4. Research Opportunities",
        "## 5. Preliminary Research Objectives",
        "## 6. Bibliography",
        "## 7. Processing Warnings",
        "## Important Disclaimer",
    ]

    for section in required_sections:
        assert section in content, (
            "Missing report section: " + section
        )

    assert "Synthetic CNN Study" in content
    assert "Synthetic Transformer Study" in content

    assert "1000 labelled images." in content
    assert "2000 labelled images." in content

    assert "only one institution" in content

    assert "https://example.org/synthetic-a" in content
    assert "https://example.org/synthetic-b" in content

    assert "Simulated temporary API failure" in content

    assert "abstract-derived evidence" in content

    print("All required report sections found.")
    print("Paper sources preserved.")
    print("Research opportunity included.")
    print("Processing warning included.")
    print("Evidence-scope disclaimer included.")

    print("\n========== REPORT PREVIEW ==========\n")

    print(content[:2500])

    print(
        "\nTEST PASSED: Research Report Exporter "
        "works correctly."
    )


if __name__ == "__main__":
    main()
