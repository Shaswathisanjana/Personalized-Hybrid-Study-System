from app.research_agent.models import ResearchPaper
from app.research_agent.research_workflow import IntegratedResearchWorkflow
from app.research_agent.streamlit_results import (
    display_advanced_research_results,
)
from test_research_workflow_offline import MockSummarizer

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
        title="Deep Learning in Medical Image Classification",
        authors=["Test Author B"],
        abstract="Deep Learning in Medical Image Classification - 1",
        url="https://doi.org/10.1201/9781003038450-9",
        year=2025,
    ),
]

workflow = IntegratedResearchWorkflow(
    summarizer=MockSummarizer(),
)

result = workflow.run(
    topic="Medical Image Classification",
    papers=papers,
    include_thematic_review=False,
)

display_advanced_research_results(result)
