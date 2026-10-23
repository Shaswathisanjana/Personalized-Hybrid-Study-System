from app.research_agent.models import ResearchPaper
from app.research_agent.research_workflow import IntegratedResearchWorkflow
from app.research_agent.report_exporter import ResearchReportExporter

from test_research_workflow_offline import MockSummarizer


def main():

    valid_paper = ResearchPaper(
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
    )

    invalid_paper = ResearchPaper(
        title="Deep Learning in Medical Image Classification",
        authors=["Test Author B"],
        abstract=(
            "Deep Learning in Medical Image Classification - 1"
        ),
        url="https://doi.org/10.1201/9781003038450-9",
        year=2025,
    )

    workflow = IntegratedResearchWorkflow(
        summarizer=MockSummarizer(),
    )

    result = workflow.run(
        topic="Medical Image Classification",
        papers=[valid_paper, invalid_paper],
        include_thematic_review=False,
    )

    assert len(result.papers) == 2
    assert len(result.accepted_papers) == 1
    assert len(result.excluded_papers) == 1
    assert len(result.summaries) == 1

    report = ResearchReportExporter.build_markdown(result)

    assert "**Papers retrieved:** 2" in report
    assert "**Papers accepted:** 1" in report
    assert "**Papers excluded:** 1" in report
    assert "**Papers summarized:** 1" in report

    assert "### Abstract Quality Validation" in report
    assert (
        "**Excluded: Deep Learning in Medical Image Classification**"
        in report
    )
    assert "title-like placeholder" in report

    assert "1000 labelled images." in report
    assert "**Simple Summary:**" in report
    assert "**Detailed Structured Summary:**" in report

    print("Retrieved:", len(result.papers))
    print("Accepted:", len(result.accepted_papers))
    print("Excluded:", len(result.excluded_papers))
    print("Summarized:", len(result.summaries))

    print(
        "\nTEST PASSED: Excluded-paper information "
        "appears correctly in the research report."
    )


if __name__ == "__main__":
    main()
