from pathlib import Path

path = Path("app/research_agent/research_workflow.py")
source = path.read_text(encoding="utf-8-sig")

old_import = "from app.research_agent.paper_search import AcademicPaperSearch"
new_import = (
    "from app.research_agent.paper_search import AcademicPaperSearch\n"
    "from app.research_agent.autonomous_search import (\n"
    "    AutonomousResearchSearcher,\n"
    "    SearchAttempt,\n"
    ")"
)

old_field = '    source_scope: str = "abstract_only"'
new_field = (
    '    source_scope: str = "abstract_only"\n'
    '    search_attempts: list[SearchAttempt] = field(default_factory=list)'
)

old_signature = (
    "        papers: list[ResearchPaper] | None = None,\n"
    "        include_thematic_review: bool = True,\n"
    "    ) -> ResearchWorkflowResult:"
)

new_signature = (
    "        papers: list[ResearchPaper] | None = None,\n"
    "        include_thematic_review: bool = True,\n"
    "        search_queries: list[str] | None = None,\n"
    "    ) -> ResearchWorkflowResult:"
)

old_search = """        if papers is not None:
            result.papers = list(papers)
        else:
            search = (
                self.search_service
                if self.search_service is not None
                else AcademicPaperSearch()
            )

            search_result = search.search(
                query=result.topic,
                limit=limit,
            )

            result.papers = list(search_result.papers)

            result.warnings.extend(
                search_result.provider_errors
            )
"""

new_search = """        if papers is not None:
            result.papers = list(papers)

        elif search_queries is not None:
            searcher = AutonomousResearchSearcher(
                search_service=self.search_service,
                max_attempts=3,
            )

            refined = searcher.search(
                queries=search_queries,
                limit=limit,
                target_usable_papers=min(2, limit),
            )

            result.papers = list(refined.papers)
            result.search_attempts = list(refined.attempts)
            result.warnings.extend(refined.warnings)

        else:
            search = (
                self.search_service
                if self.search_service is not None
                else AcademicPaperSearch()
            )

            search_result = search.search(
                query=result.topic,
                limit=limit,
            )

            result.papers = list(search_result.papers)

            result.warnings.extend(
                search_result.provider_errors
            )
"""

changes = [
    (old_import, new_import, "import"),
    (old_field, new_field, "result field"),
    (old_signature, new_signature, "run signature"),
    (old_search, new_search, "search routing"),
]

for old, new, label in changes:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(
            f"Expected exactly one {label} match; found {count}. "
            "No changes were written."
        )

for old, new, label in changes:
    source = source.replace(old, new, 1)

compile(source, str(path), "exec")

backup = path.with_suffix(".py.bak")
backup.write_text(path.read_text(encoding="utf-8-sig"), encoding="utf-8")
path.write_text(source, encoding="utf-8")

print("PASS: Autonomous search integrated into research workflow.")
print("PASS: Original workflow backed up.")
print("PASS: Python syntax validation.")
