from app.cognitive.models import StudentCognitiveModel
from app.learning_agent.resources.models import LearningResource
from app.learning_agent.resources.resource_recommender import (
    LearningResourceRecommender,
)


def resource(title, url):
    return LearningResource(
        title=title,
        url=url,
        resource_type="video",
        description="An educational tutorial.",
        source="Controlled Test",
        difficulty="easy",
        topics=["Python recursion"],
    )


class FakeRetriever:
    def search(self, concept_name, max_results=10, target_level=None):
        print("Requested concept:", concept_name)
        print("CACM target level:", target_level)

        assert concept_name == "Python recursion"
        assert target_level == "easy"

        return [
            resource(
                "Python Recursion Tutorial for Beginners",
                "https://example.com/python-recursion",
            ),
            resource(
                "Recursion in Java Full Tutorial",
                "https://example.com/java-recursion",
            ),
            resource(
                "Complete Python Installation Guide",
                "https://example.com/python-install",
            ),
            resource(
                "Understanding Recursive Functions in Python",
                "https://example.com/python-recursive",
            ),
            resource(
                "Recursion in C Programming",
                "https://example.com/c-recursion",
            ),
        ]


student = StudentCognitiveModel(
    user_id="controlled_resource_test"
)

recommender = LearningResourceRecommender(
    retriever=FakeRetriever()
)

result = recommender.recommend(
    student=student,
    concept_name="Python recursion",
    top_k=10,
    candidate_count=10,
)

titles = [
    item.resource.title
    for item in result.resources
]

scores = [
    item.final_score
    for item in result.resources
]

print("\n========== CONTROLLED INTEGRATION TEST ==========")
print("Student level:", result.student_level)
print("Recommended count:", len(titles))

for index, item in enumerate(result.resources, start=1):
    print(
        f"{index}. {item.resource.title} "
        f"| Score: {item.final_score:.3f}"
    )

assert result.student_level == "easy"
assert len(titles) == 2, (
    f"Expected exactly 2 relevant resources, got {len(titles)}"
)

assert "Python Recursion Tutorial for Beginners" in titles
assert "Understanding Recursive Functions in Python" in titles

assert "Recursion in Java Full Tutorial" not in titles
assert "Complete Python Installation Guide" not in titles
assert "Recursion in C Programming" not in titles

assert scores == sorted(scores, reverse=True), (
    "Resources are not sorted by descending ranking score."
)

print("\nSTEP 29 TEST PASSED")
