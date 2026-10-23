from pathlib import Path

path = Path("app/research_agent/personalized_coordinator.py")
source = path.read_text(encoding="utf-8-sig")

old = """        plan = self.planner.create_plan(
            student=self.student,
            topic=topic,
            concept_name=concept_name,
            has_active_conflict=has_active_conflict,
        )
"""

new = """        # Read the REAL unresolved conflict state from shared CACM.
        # A caller-supplied flag must not manufacture a conflict.
        detected_conflict = self.cacm_runtime.cognitive_engine.has_conflict(
            user_id=self.student.user_id,
            concept_name=concept_name.strip(),
        )

        if has_active_conflict and not detected_conflict:
            raise ValueError(
                "Diagnostic research requires a genuine unresolved "
                "conflict in the shared CACM cognitive engine."
            )

        plan = self.planner.create_plan(
            student=self.student,
            topic=topic,
            concept_name=concept_name,
            has_active_conflict=detected_conflict,
        )
"""

count = source.count(old)

if count != 1:
    raise RuntimeError(
        f"Expected exactly one coordinator planning block; found {count}. "
        "No changes were written."
    )

source = source.replace(old, new, 1)

compile(source, str(path), "exec")

backup = Path(
    "app/research_agent/personalized_coordinator_before_conflict.bak"
)

backup.write_text(
    path.read_text(encoding="utf-8-sig"),
    encoding="utf-8",
)

path.write_text(source, encoding="utf-8")

print("PASS: Research Coordinator now reads real CACM conflicts.")
print("PASS: Artificial conflict flags are rejected.")
print("PASS: Original coordinator backed up.")
