from pathlib import Path

path = Path("app/research_agent/report_exporter.py")

backup = Path(
    "app/research_agent/"
    "report_exporter_before_quality_display.py.bak"
)

if not backup.exists():
    raise RuntimeError(
        "Original report backup was not found. "
        "No changes were made."
    )

original = backup.read_text(encoding="utf-8-sig")

anchor = '''            f"**Papers summarized:** {len(result.summaries)}",
            "",
            "---",
'''

replacement = '''            f"**Papers accepted:** {len(result.accepted_papers)}",
            "",
            f"**Papers excluded:** {len(result.excluded_papers)}",
            "",
            f"**Papers summarized:** {len(result.summaries)}",
            "",
            "### Abstract Quality Validation",
            "",
            "The following decisions use heuristic checks on "
            "retrieved abstracts. Exclusion does not imply "
            "that a publication is academically poor.",
            "",
        ]

        if result.excluded_papers:
            for paper, quality in result.excluded_papers:
                lines.extend([
                    f"**Excluded: {paper.title}**",
                    "",
                    f"- Status: {quality.status}",
                    f"- Reason: {quality.reason}",
                    f"- Retrieved abstract words: {quality.word_count}",
                    f"- Source: {paper.url}",
                    "",
                ])
        else:
            lines.extend([
                "No retrieved papers were excluded by the "
                "abstract-quality validator.",
                "",
            ])

        lines.extend([
            "---",
'''

if original.count(anchor) != 1:
    raise RuntimeError(
        "Expected insertion point not found exactly once. "
        "No changes were made."
    )

corrected = original.replace(anchor, replacement, 1)

# Validate the corrected source BEFORE replacing the file.
compile(
    corrected,
    str(path),
    "exec",
)

path.write_text(corrected, encoding="utf-8")

print("SUCCESS: Report exporter repaired.")
print("Original Simple Summary and Detailed Structured Summary preserved.")
