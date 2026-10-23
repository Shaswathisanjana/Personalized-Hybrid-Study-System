from app.research_agent.models import ResearchPaper
from app.research_agent.research_workflow import IntegratedResearchWorkflow


GOOD_ABSTRACT = (
    "Medical image classification is an important task in "
    "computer-aided diagnosis. This study investigates a "
    "convolutional neural network for identifying disease "
    "patterns in medical images. The approach uses labelled "
    "training data and evaluates classification performance "
    "using accuracy, precision, recall, and F1-score. "
    "The experimental analysis compares the proposed model "
    "against baseline classification methods and discusses "
    "the limitations of the available dataset."
)


class RecordingSummarizer:
    def __init__(self):
        self.received_papers = []

    def summarize_multiple(self, papers):
        self.received_papers = list(papers)

        # Returning no summaries is intentional:
        # this test isolates the filtering stage.
        return []


def make_paper(title, abstract):
    return ResearchPaper(
        title=title,
        authors=["Test Author"],
        abstract=abstract,
        url="https://example.org/test-paper",
        year=2025,
        source="synthetic-test",
    )


def main():
    good = make_paper(
        "Medical Image Classification Using CNN",
        GOOD_ABSTRACT,
    )

    placeholder = make_paper(
        "Deep Learning in Medical Image Classification",
        "Deep Learning in Medical Image Classification - 1",
    )

    empty = make_paper(
        "Paper Without Abstract",
        "",
    )

    summarizer = RecordingSummarizer()

    workflow = IntegratedResearchWorkflow(
        summarizer=summarizer,
    )

    result = workflow.run(
        topic="Medical Image Classification",
        papers=[good, placeholder, empty],
        include_thematic_review=False,
    )

    assert len(result.papers) == 3
    assert len(result.accepted_papers) == 1
    assert len(result.excluded_papers) == 2

    assert result.accepted_papers[0].title == good.title

    assert len(summarizer.received_papers) == 1
    assert summarizer.received_papers[0].title == good.title

    print("Retrieved papers:", len(result.papers))
    print("Accepted papers:", len(result.accepted_papers))
    print("Excluded papers:", len(result.excluded_papers))

    for paper, quality in result.excluded_papers:
        print("\nExcluded:", paper.title)
        print("Status:", quality.status)
        print("Reason:", quality.reason)

    print(
        "\nTEST PASSED: Unusable abstracts are excluded "
        "before summarization."
    )


if __name__ == "__main__":
    main()
