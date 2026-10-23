from app.cognitive.models import StudentCognitiveModel
from app.learning_agent.progress_tracker import LearningProgressTracker


tracker = LearningProgressTracker()

alice = StudentCognitiveModel(user_id="student_alice")
bob = StudentCognitiveModel(user_id="student_bob")

print("\n========== TEST 1: STARTING A TOPIC ==========")

first = tracker.start_topic(
    alice.user_id,
    "Python Recursion",
)

assert first.status == "started"
assert first.completed_practice_sessions == 0
assert first.total_practice_questions == 0
assert len(first.events) == 1
assert first.events[0].event_type == "topic_started"

# Opening a topic must not create cognitive evidence.
assert alice.concepts == {}

print("PASS: Topic started without modifying CACM.")


print("\n========== TEST 2: REPEATED VISITS ==========")

second = tracker.start_topic(
    alice.user_id,
    "python recursion",
)

assert first is second
assert len(first.events) == 1

print("PASS: Reopening a topic does not duplicate its record.")


print("\n========== TEST 3: COMPLETED PRACTICE SESSION ==========")

tracker.complete_practice_session(
    alice.user_id,
    "Python Recursion",
    questions_completed=10,
)

record = tracker.get_progress(
    alice.user_id,
    "Python Recursion",
)

assert record.status == "practice_completed"
assert record.completed_practice_sessions == 1
assert record.total_practice_questions == 10
assert len(record.events) == 2

# A completed quiz is an activity milestone,
# not automatic proof of mastery.
assert alice.concepts == {}

print("PASS: Practice completion recorded independently of mastery.")


print("\n========== TEST 4: MULTIPLE SESSIONS ==========")

tracker.complete_practice_session(
    alice.user_id,
    "Python Recursion",
    questions_completed=5,
)

assert record.completed_practice_sessions == 2
assert record.total_practice_questions == 15
assert len(record.events) == 3

print("PASS: Multiple sessions accumulate correctly.")


print("\n========== TEST 5: STUDENT ISOLATION ==========")

assert tracker.get_progress(
    bob.user_id,
    "Python Recursion",
) is None

tracker.start_topic(
    bob.user_id,
    "Python Recursion",
)

assert tracker.get_progress(
    bob.user_id,
    "Python Recursion",
).status == "started"

assert tracker.get_progress(
    alice.user_id,
    "Python Recursion",
).completed_practice_sessions == 2

print("PASS: Students have independent progress records.")


print("\n========== TEST 6: CACM SNAPSHOT ==========")

state = alice.get_concept("Python Recursion")
state.mastery = 0.74
state.confidence = 0.36
state.attempts = 15

snapshot = tracker.snapshot(
    alice,
    "Python Recursion",
)

assert snapshot.mastery == 0.74
assert snapshot.confidence == 0.36
assert snapshot.cognitive_attempts == 15
assert snapshot.completed_practice_sessions == 2
assert snapshot.total_practice_questions == 15

# The snapshot must read CACM, not recalculate it.
assert state.mastery == 0.74
assert state.confidence == 0.36
assert state.attempts == 15

print("PASS: Snapshot reads the existing CACM state.")


print("\n========== TEST 7: INVALID COMPLETION ==========")

try:
    tracker.complete_practice_session(
        alice.user_id,
        "Arrays",
        questions_completed=0,
    )
except ValueError:
    pass
else:
    raise AssertionError(
        "Zero-question completion should be rejected."
    )

assert tracker.get_progress(
    alice.user_id,
    "Arrays",
) is None

print("PASS: Invalid completion rejected without creating a record.")


print("\n========== TEST 8: TOPIC LISTING ==========")

tracker.start_topic(
    alice.user_id,
    "Arrays",
)

alice_topics = tracker.list_progress(
    alice.user_id,
)

assert len(alice_topics) == 2
assert {
    item.topic_name for item in alice_topics
} == {"Python Recursion", "Arrays"}

assert len(tracker.list_progress(bob.user_id)) == 1

print("PASS: Topic listing respects student boundaries.")


print("\nSTEP 65: ALL PROGRESS TRACKER TESTS PASSED")
