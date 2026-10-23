from collections import Counter

from app.cognitive.models import StudentCognitiveModel
from app.learning_agent.resources.resource_recommender import (
    LearningResourceRecommender,
)
from app.learning_agent.resources.relevance_guard import (
    ResourceRelevanceGuard,
)


class CachedRetriever:
    def __init__(self, resources):
        self.resources = resources

    def search(self, concept_name, max_results=10, target_level=None):
        return self.resources[:max_results]


print("\n========== FETCH RESOURCE POOL ==========")

live_recommender = LearningResourceRecommender()

resources = live_recommender.retriever.search(
    concept_name="Python recursion",
    max_results=20,
    target_level="easy",
)

print("Retrieved:", len(resources))

print("\n========== RELEVANCE FILTER ==========")

guard = ResourceRelevanceGuard()

accepted = []
rejected = []

for resource in resources:
    if guard.is_relevant(
        concept_name="Python recursion",
        resource=resource,
    ):
        accepted.append(resource)
    else:
        rejected.append(resource)

print("Accepted:", len(accepted))
print("Rejected:", len(rejected))

for resource in rejected:
    print("REJECTED:", resource.title)

print("\n========== FINAL PERSONALIZED RANKING ==========")

student = StudentCognitiveModel(user_id="step42_test_student")

recommender = LearningResourceRecommender(
    retriever=CachedRetriever(resources),
)

result = recommender.recommend(
    student=student,
    concept_name="Python recursion",
    top_k=20,
    candidate_count=20,
)

print("CACM student level:", result.student_level)
print("Final recommendation count:", len(result.resources))

sources = Counter()

for index, ranked in enumerate(result.resources, start=1):
    resource = ranked.resource
    sources[resource.source.split(" - ")[0]] += 1

    print(
        f"{index}. [{resource.source}] "
        f"{resource.title}"
    )
    print(f"   Score: {ranked.final_score:.3f}")
    print(f"   URL: {resource.url}")

print("\nFinal source distribution:", dict(sources))

assert all(
    guard.is_relevant(
        concept_name="Python recursion",
        resource=ranked.resource,
    )
    for ranked in result.resources
), "An irrelevant resource bypassed the relevance guard."

assert all(
    result.resources[i].final_score
    >= result.resources[i + 1].final_score
    for i in range(len(result.resources) - 1)
), "Final resources are not sorted by ranking score."

print("\nSTEP 42 FINAL RANKING TEST PASSED")
