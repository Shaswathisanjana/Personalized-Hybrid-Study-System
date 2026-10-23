from pathlib import Path

path = Path("test_intelligent_research_integration.py")

source = path.read_text(encoding="utf-8-sig")

old_import = """from app.cognitive.cognitive_engine import CognitiveEngine
"""

new_import = """from app.cognitive.cognitive_engine import CognitiveEngine
from app.cognitive.evidence import LearningEvidence
"""

old_engine = """    workflow = MockResearchWorkflow()

    coordinator = PersonalizedResearchCoordinator(
        student=student,
        cognitive_engine=CognitiveEngine(),
        workflow=workflow,
    )
"""

new_engine = """    workflow = MockResearchWorkflow()
    engine = CognitiveEngine()

    coordinator = PersonalizedResearchCoordinator(
        student=student,
        cognitive_engine=engine,
        workflow=workflow,
    )
"""

old_conflict = """    result = coordinator.conduct_research(
        topic="Deep Learning for Medical Images",
        concept_name="Deep Learning",
        has_active_conflict=True,
        papers=[],
    )

    assert result.action.action_type == "diagnostic_research"
    assert result.plan.action.action_type == "diagnostic_research"

    print("PASS: Cross-agent conflict selects diagnostic research.")

    assert state.attempts == 0
    assert state.mastery == 0.5

    print("PASS: Diagnostic planning does not fabricate assessment evidence.")
"""

new_conflict = """    # Create actual contradictory observations in the shared CACM
    # engine. An artificial conflict flag alone is no longer accepted.
    engine.process_evidence(
        student,
        LearningEvidence(
            user_id=student.user_id,
            concept_name="Deep Learning",
            source_agent="learning",
            evidence_type="quiz",
            performance=0.95,
            difficulty=0.70,
            reliability=0.90,
        ),
    )

    engine.process_evidence(
        student,
        LearningEvidence(
            user_id=student.user_id,
            concept_name="Deep Learning",
            source_agent="coding",
            evidence_type="coding_solution",
            performance=0.15,
            difficulty=0.70,
            reliability=0.90,
        ),
    )

    assert engine.has_conflict(student.user_id, "Deep Learning")
    print("PASS: Genuine cross-agent conflict established.")

    attempts_before = state.attempts
    mastery_before = state.mastery

    result = coordinator.conduct_research(
        topic="Deep Learning for Medical Images",
        concept_name="Deep Learning",
        papers=[],
    )

    assert result.action.action_type == "diagnostic_research"
    assert result.plan.action.action_type == "diagnostic_research"

    print("PASS: Real cross-agent conflict selects diagnostic research.")

    assert state.attempts == attempts_before
    assert state.mastery == mastery_before
    assert engine.has_conflict(student.user_id, "Deep Learning")

    print("PASS: Diagnostic planning does not fabricate assessment evidence.")
"""

replacements = [
    (old_import, new_import, "evidence import"),
    (old_engine, new_engine, "shared cognitive engine"),
    (old_conflict, new_conflict, "genuine conflict scenario"),
]

for old, new, label in replacements:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(
            f"Expected exactly one {label} block; found {count}. "
            "No changes were written."
        )
    source = source.replace(old, new, 1)

compile(source, str(path), "exec")

backup = Path(
    "test_intelligent_research_integration_before_conflict_fix.bak"
)

backup.write_text(
    path.read_text(encoding="utf-8-sig"),
    encoding="utf-8",
)

path.write_text(source, encoding="utf-8")

print("PASS: Original integration test backed up.")
print("PASS: Genuine cross-agent evidence added.")
print("PASS: Shared CACM engine reused.")
print("PASS: Updated test syntax validated.")
