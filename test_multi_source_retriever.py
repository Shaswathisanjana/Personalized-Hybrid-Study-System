from app.learning_agent.resources.models import LearningResource
from app.learning_agent.resources.multi_source_retriever import (
    MultiSourceResourceRetriever,
)


class FakeSource:
    def __init__(self, name, urls):
        self.name = name
        self.urls = urls

    def search(self, concept_name, max_results, target_level):
        return [
            LearningResource(
                title=f"{concept_name} {self.name} {i}",
                url=url,
                resource_type="tutorial",
                source=self.name,
                difficulty=target_level or "medium",
                topics=[concept_name],
            )
            for i, url in enumerate(self.urls)
        ]


class BrokenSource:
    def search(self, concept_name, max_results, target_level):
        raise RuntimeError("Simulated API failure")


youtube = FakeSource(
    "YouTube",
    [
        "https://example.com/video1",
        "https://example.com/video2",
        "https://example.com/video3",
    ],
)

articles = FakeSource(
    "Articles",
    [
        "https://example.com/article1",
        "https://example.com/video1",
        "https://example.com/article2",
    ],
)

retriever = MultiSourceResourceRetriever(
    [youtube, BrokenSource(), articles]
)

results = retriever.search(
    concept_name="Recursion",
    max_results=5,
    target_level="easy",
)

sources = [resource.source for resource in results]
urls = [resource.url for resource in results]

print("Returned sources:", sources)
print("Returned count:", len(results))
print("Unique URLs:", len(set(urls)))

assert len(results) == 5
assert len(set(urls)) == 5
assert sources[0] == "YouTube"
assert sources[1] == "Articles"
assert "Articles" in sources
assert "YouTube" in sources

print("STEP 14 TEST PASSED")
