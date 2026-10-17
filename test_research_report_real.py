from pathlib import Path

from app.research_agent.research_workflow import (
    IntegratedResearchWorkflow,
)
from app.research_agent.report_exporter import (
    ResearchReportExporter,
)


def main():

    topic = "Deep Learning for Medical Image Classification"

    print("\n========== REAL RESEARCH REPORT GENERATION ==========")

    print("Topic:", topic)
    print("Requested papers: 2")

    workflow = IntegratedResearchWorkflow()

    print("\nSTEP 1: Retrieving and analyzing academic papers...")

    result = workflow.run(
        topic=topic,
        limit=2,
        include_thematic_review=False,
    )

    print("Retrieved papers:", len(result.papers))
    print("Structured summaries:", len(result.summaries))

    if not result.summaries:
        print(
            "\nNo structured summaries were produced. "
            "Report export has been skipped."
        )
        return

    print("\nSTEP 2: Exporting the research report...")

    output_path = (
        "data/research_reports/"
        "real_medical_imaging_research_report.md"
    )

    exported_path = ResearchReportExporter.export(
        result=result,
        output_path=output_path,
    )

    print("Report saved:", exported_path.resolve())

    print("\nSTEP 3: Checking the generated report...")

    assert exported_path.exists()

    content = exported_path.read_text(
        encoding="utf-8"
    )

    assert "# Academic Research Analysis Report" in content
    assert "## 1. Structured Paper Summaries" in content
    assert "## 6. Bibliography" in content
    assert "## Important Disclaimer" in content

    print("Report size:", len(content), "characters")
    print("Bibliography included.")
    print("Evidence-scope disclaimer included.")

    print("\n========== PAPER SOURCES ==========")

    for paper in result.papers:
        print("-", paper.title)
        print(" ", paper.url)

    print("\n========== WARNINGS ==========")

    if result.warnings:
        for warning in result.warnings:
            print("-", warning)
    else:
        print("No processing warnings.")

    print(
        "\nTEST PASSED: Real academic research report "
        "generated successfully."
    )


if __name__ == "__main__":
    main()
