from app.learning_agent.resources.models import LearningResource
from app.learning_agent.resources.resource_ranker import LearningResourceRanker

ranker = LearningResourceRanker()


def make_resource(title, description, topics):
    return LearningResource(
        title=title,
        url="https://example.com/test",
        resource_type="article",
        description=description,
        source="Controlled Test",
        difficulty="easy",
        topics=topics,
    )


print("\n========== TOPIC-TAG INDEPENDENCE TEST ==========")

plain = make_resource(
    title="Python Installation Guide",
    description="How to install Python on Windows.",
    topics=[],
)

tagged = make_resource(
    title="Python Installation Guide",
    description="How to install Python on Windows.",
    topics=["Python recursion"],
)

plain_score = ranker._relevance_score(
    concept_name="Python recursion",
    resource=plain,
)

tagged_score = ranker._relevance_score(
    concept_name="Python recursion",
    resource=tagged,
)

print("Without search-derived topic tag:", round(plain_score, 4))
print("With search-derived topic tag:   ", round(tagged_score, 4))

assert abs(plain_score - tagged_score) < 1e-12, (
    "Search-derived topic tags incorrectly changed relevance."
)

print("\n========== GENUINE TITLE RELEVANCE TEST ==========")

relevant = make_resource(
    title="Python Recursion Tutorial",
    description="Learn recursive functions with examples.",
    topics=[],
)

relevant_score = ranker._relevance_score(
    concept_name="Python recursion",
    resource=relevant,
)

print("Relevant resource score:", round(relevant_score, 4))

assert relevant_score > plain_score, (
    "Genuinely relevant title did not receive a higher score."
)

print("\nSTEP 33 TEST PASSED")
