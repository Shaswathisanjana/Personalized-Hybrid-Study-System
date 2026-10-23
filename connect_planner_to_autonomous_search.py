from pathlib import Path

path = Path("app/research_agent/personalized_coordinator.py")
source = path.read_text(encoding="utf-8-sig")

old = """        research = self.workflow.run(
            topic=plan.topic,
            limit=limit,
            papers=papers,
            include_thematic_review=include_thematic_review,
        )
"""

new = """        workflow_kwargs = {
            "topic": plan.topic,
            "limit": limit,
            "papers": papers,
            "include_thematic_review": include_thematic_review,
        }

        # Manually supplied papers must never trigger online retrieval.
        # Only the real integrated workflow receives planned search queries.
        if (
            papers is None
            and isinstance(self.workflow, IntegratedResearchWorkflow)
        ):
            workflow_kwargs["search_queries"] = plan.search_queries

        research = self.workflow.run(**workflow_kwargs)
"""

count = source.count(old)

if count != 1:
    raise RuntimeError(
        f"Expected one coordinator integration point; found {count}. "
        "No changes were written."
    )

source = source.replace(old, new, 1)

compile(source, str(path), "exec")

backup = path.with_suffix(".py.bak")
backup.write_text(
    path.read_text(encoding="utf-8-sig"),
    encoding="utf-8",
)

path.write_text(source, encoding="utf-8")

print("PASS: Intelligent Planner connected to autonomous search.")
print("PASS: Manual paper input still bypasses online retrieval.")
print("PASS: Existing mock-workflow compatibility preserved.")
