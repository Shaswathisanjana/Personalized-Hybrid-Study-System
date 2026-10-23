from dataclasses import dataclass

from app.learning_agent.resources.format_filter import (
    RESOURCE_FORMATS,
    filter_ranked_resources,
)


@dataclass
class FakeResource:
    resource_type: str


@dataclass
class FakeRankedResource:
    resource: FakeResource
    final_score: float


items = [
    FakeRankedResource(FakeResource("video"), 0.95),
    FakeRankedResource(FakeResource("video"), 0.90),
    FakeRankedResource(FakeResource("article"), 0.75),
    FakeRankedResource(FakeResource("documentation"), 0.70),
    FakeRankedResource(FakeResource("tutorial"), 0.65),
    FakeRankedResource(FakeResource("webpage"), 0.60),
]

expected_counts = {
    "All Resources": 6,
    "Videos": 2,
    "Articles": 3,
    "Documentation": 1,
}

print("\n========== RESOURCE FORMAT FILTER TEST ==========")

original_scores = [item.final_score for item in items]

for selected_format in RESOURCE_FORMATS:
    result = filter_ranked_resources(items, selected_format)

    assert len(result) == expected_counts[selected_format]

    scores = [item.final_score for item in result]

    assert scores == sorted(scores, reverse=True), (
        f"Original ranking order changed for {selected_format}"
    )

    print(
        f"PASS: {selected_format} -> "
        f"{len(result)} resources; scores {scores}"
    )

assert [item.final_score for item in items] == original_scores, (
    "Original recommendations were modified."
)

try:
    filter_ranked_resources(items, "Invalid Format")
    raise AssertionError("Invalid format was accepted.")
except ValueError:
    print("PASS: Invalid format rejected")

print("\nSTEP 44 ALL TESTS PASSED")
