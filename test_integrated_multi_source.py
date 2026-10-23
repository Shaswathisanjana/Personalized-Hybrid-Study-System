from app.cognitive.models import StudentCognitiveModel

from app.learning_agent.resources.resource_recommender import (
    LearningResourceRecommender,
)

from app.learning_agent.resources.multi_source_retriever import (
    MultiSourceResourceRetriever,
)


student = StudentCognitiveModel(user_id="resource_integration_test")

recommender = LearningResourceRecommender()

assert isinstance(
    recommender.retriever,
    MultiSourceResourceRetriever,
), "The multi-source retriever is not connected."

print("\n========== INTEGRATED RESOURCE TEST ==========")

try:
    recommendation = recommender.recommend(
        student=student,
        concept_name="Recursion",
        top_k=10,
        candidate_count=12,
    )

except Exception as exc:
    print("INTEGRATION ERROR:", type(exc).__name__, str(exc))
    raise SystemExit(2)


print("Target level:", recommendation.student_level)
print("Ranked recommendations:", len(recommendation.resources))

for index, ranked in enumerate(recommendation.resources, start=1):
    resource = ranked.resource

    print(f"\n{index}. {resource.title}")
    print("Source:", resource.source)
    print("Type:", resource.resource_type)
    print("Difficulty:", resource.difficulty)
    print("Ranking score:", round(ranked.final_score, 3))
    print("URL:", resource.url)


assert recommendation.student_level == "easy"
assert recommendation.resources, "No resources were recommended."

print("\nSTEP 18 TEST PASSED")

