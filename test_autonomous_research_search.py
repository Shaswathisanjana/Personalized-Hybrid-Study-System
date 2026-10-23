from types import SimpleNamespace

from app.research_agent.models import ResearchPaper
from app.research_agent.autonomous_search import AutonomousResearchSearcher


def make_paper(title, abstract, paper_id):
    return ResearchPaper(
        title=title,
        authors=["Test Author"],
        abstract=abstract,
        url=f"https://example.org/{paper_id}",
        year=2025,
        source="offline_test",
        paper_id=paper_id,
    )


GOOD_ABSTRACT = (
    "This study investigates machine learning approaches for medical "
    "image analysis using a comparative experimental methodology. "
    "The authors describe their model architecture, dataset preparation, "
    "training procedure, and evaluation process. Results are discussed "
    "alongside practical challenges, methodological limitations, and "
    "opportunities for future investigation in clinical applications."
)


class MockSearchService:

    def __init__(self):
        self.calls = []

    def search(self, query, limit=5):
        self.calls.append(query)

        if query == "initial query":
            return SimpleNamespace(
                papers=[
                    make_paper(
                        "Unsuitable Paper",
                        "Unsuitable Paper",
                        "paper_1",
                    )
                ],
                provider_errors=[],
            )

        if query == "refined query":
            return SimpleNamespace(
                papers=[
                    make_paper(
                        "Usable Paper A",
                        GOOD_ABSTRACT,
                        "paper_2",
                    ),
                    make_paper(
                        "Usable Paper B",
                        GOOD_ABSTRACT,
                        "paper_3",
                    ),
                    make_paper(
                        "Duplicate Paper A",
                        GOOD_ABSTRACT,
                        "paper_2",
                    ),
                ],
                provider_errors=[],
            )

        raise RuntimeError("Unexpected search query")


class FailingFirstSearchService(MockSearchService):

    def search(self, query, limit=5):
        if query == "initial query":
            self.calls.append(query)
            raise RuntimeError("Simulated provider failure")

        return super().search(query, limit)


def main():

    service = MockSearchService()

    searcher = AutonomousResearchSearcher(
        search_service=service,
        max_attempts=3,
    )

    result = searcher.search(
        queries=[
            "initial query",
            "refined query",
            "unused query",
        ],
        limit=3,
        target_usable_papers=2,
    )

    assert result.target_reached is True
    assert len(result.attempts) == 2
    assert service.calls == [
        "initial query",
        "refined query",
    ]

    print("PASS: Agent refined the search after insufficient results.")
    print("Queries executed:", service.calls)

    assert result.attempts[0].usable_count == 0
    assert result.attempts[1].usable_count == 2
    assert len(result.papers) == 3

    print("PASS: Abstract validation and deduplication work.")
    print("Unique papers retrieved:", len(result.papers))

    failing_service = FailingFirstSearchService()

    fallback_searcher = AutonomousResearchSearcher(
        search_service=failing_service,
        max_attempts=3,
    )

    fallback_result = fallback_searcher.search(
        queries=["initial query", "refined query"],
        target_usable_papers=2,
    )

    assert fallback_result.target_reached is True
    assert len(fallback_result.warnings) >= 1
    assert failing_service.calls == [
        "initial query",
        "refined query",
    ]

    print("PASS: Agent recovered from a failed search provider.")

    print()
    print("ALL AUTONOMOUS SEARCH TESTS PASSED.")


if __name__ == "__main__":
    main()
