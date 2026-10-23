from collections import Counter

from app.cognitive.models import StudentCognitiveModel
from app.learning_agent.resources.resource_recommender import (
    LearningResourceRecommender,
)
from app.learning_agent.resources.relevance_guard import (
    ResourceRelevanceGuard,
)

student = StudentCognitiveModel(
    user_id="live_resource_quality_test"
)

recommender = LearningResourceRecommender()
guard = ResourceRelevanceGuard()

concept = "Python recursion"

print("\n========== LIVE RESOURCE RETRIEVAL ==========")

level = recommender._determine_student_level(
    mastery=student.get_concept(concept).mastery,
    confidence=student.get_concept(concept).confidence,
    attempts=student.get_concept(concept).attempts,
)

candidates = recommender.retriever.search(
    concept_name=concept,
    max_results=20,
    target_level=level,
)

accepted = [
    r for r in candidates
    if guard.is_relevant(concept, r)
]

rejected = [
    r for r in candidates
    if not guard.is_relevant(concept, r)
]

print("CACM target level:", level)
print("Retrieved candidates:", len(candidates))
print("Accepted candidates:", len(accepted))
print("Rejected candidates:", len(rejected))

print("\n========== REJECTED RESOURCES ==========")

for r in rejected:
    print("-", r.title, "|", r.source)

print("\n========== FINAL PERSONALIZED RECOMMENDATIONS ==========")

result = recommender.recommend(
    student=student,
    concept_name=concept,
    top_k=10,
    candidate_count=20,
)

for i, item in enumerate(result.resources, 1):
    r = item.resource

    print(
        f"{i}. {r.title}\n"
        f"   Source: {r.source}\n"
        f"   Difficulty: {r.difficulty}\n"
        f"   Ranking score: {item.final_score:.3f}\n"
        f"   URL: {r.url}"
    )

print("\nFinal recommendation count:", len(result.resources))

assert all(
    guard.is_relevant(concept, item.resource)
    for item in result.resources
)

assert len(result.resources) <= 10

print("\nSTEP 30 LIVE PIPELINE CHECK PASSED")
