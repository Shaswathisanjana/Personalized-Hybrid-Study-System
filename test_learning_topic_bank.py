from app.learning_agent.topic_bank import (
    LearningTopicBank,
    TOPICS,
)

bank = LearningTopicBank()

print("\n========== TOPIC BANK VALIDATION ==========")

assert len(bank.all_topics()) == 50
assert len(bank.categories()) == 5

valid_difficulties = {"easy", "medium", "hard"}

for topic in TOPICS:
    assert topic.name.strip()
    assert topic.category.strip()
    assert topic.difficulty in valid_difficulties

    for prerequisite in topic.prerequisites:
        assert bank.get(prerequisite) is not None
        assert prerequisite.casefold() != topic.name.casefold()

print("PASS: All 50 topics have valid metadata.")
print("PASS: All direct prerequisites exist.")

print("\n========== CIRCULAR DEPENDENCY CHECK ==========")

def visit(name, visiting, visited):
    key = name.casefold()

    if key in visiting:
        raise AssertionError(
            f"Circular prerequisite dependency detected: {name}"
        )

    if key in visited:
        return

    visiting.add(key)

    topic = bank.get(name)
    assert topic is not None

    for prerequisite in topic.prerequisites:
        visit(prerequisite, visiting, visited)

    visiting.remove(key)
    visited.add(key)


visited = set()

for topic in TOPICS:
    visit(topic.name, set(), visited)

assert len(visited) == 50

print("PASS: No circular prerequisite chains.")

print("\n========== SEARCH AND CATEGORY TESTS ==========")

assert bank.get("python recursion").name == "Python Recursion"
assert bank.get(" PYTHON RECURSION ").name == "Python Recursion"

recursion_results = bank.search("recursion")

assert any(
    topic.name == "Python Recursion"
    for topic in recursion_results
)

assert len(bank.search("")) == 50
assert len(bank.by_category("python")) == 11

assert [
    topic.name
    for topic in bank.prerequisites_for("Python Recursion")
] == ["Python Functions"]

assert bank.get("A custom student topic") is None

print("PASS: Case-insensitive lookup.")
print("PASS: Topic search.")
print("PASS: Category filtering.")
print("PASS: Prerequisite retrieval.")
print("PASS: Unknown topics remain distinguishable.")

print("\n========== CATEGORY COUNTS ==========")

for category in bank.categories():
    print(
        f"{category}: {len(bank.by_category(category))} topics"
    )

print("\nSTEP 58 TOPIC BANK TESTS PASSED")
