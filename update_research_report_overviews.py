from pathlib import Path

path = Path("app/research_agent/report_exporter.py")

content = path.read_text(encoding="utf-8-sig")

old_import = (
    "from app.research_agent.paper_summarizer "
    "import SUMMARY_FIELDS"
)

new_import = (
    "from app.research_agent.paper_summarizer "
    "import SUMMARY_FIELDS\n"
    "from app.research_agent.individual_paper_overview "
    "import IndividualPaperOverviewBuilder"
)

if content.count(old_import) != 1:
    raise RuntimeError(
        "Expected exactly one SUMMARY_FIELDS import. "
        "File left unchanged."
    )

old_section = '''            for field_name in SUMMARY_FIELDS:

                value = getattr(summary, field_name)'''

new_section = '''            overview = IndividualPaperOverviewBuilder.build(
                summary
            )

            lines.extend([
                "**Simple Summary:**",
                "",
                overview.simple_summary,
                "",
                "**Detailed Structured Summary:**",
                "",
            ])

            for field_name in SUMMARY_FIELDS:

                value = getattr(summary, field_name)'''

if content.count(old_section) != 1:
    raise RuntimeError(
        "Expected exactly one paper-summary insertion point. "
        "File left unchanged."
    )

updated = content.replace(
    old_import,
    new_import,
    1,
).replace(
    old_section,
    new_section,
    1,
)

compile(
    updated,
    str(path),
    "exec",
)

path.write_text(
    updated,
    encoding="utf-8",
)

print(
    "SUCCESS: Individual paper summaries added "
    "to the report exporter."
)
