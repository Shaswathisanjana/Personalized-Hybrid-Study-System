from pathlib import Path

path = Path("app/research_agent/report_exporter.py")

backup = Path(
    "app/research_agent/"
    "report_exporter_before_quality_display.py.bak"
)

if not backup.exists():
    raise RuntimeError("Original backup missing. No changes made.")

original = backup.read_text(encoding="utf-8-sig")

anchor = '''            f"**Papers summarized:** {len(result.summaries)}",
            "",
            "---",
            "",
            "## 1. Structured Paper Summaries",
            "",
        ]
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
            "",
            "## 1. Structured Paper Summaries",
            "",
        ])
'''

if original.count(anchor) != 1:
    raise RuntimeError(
        "Expected original introduction not found exactly once. "
        "No changes made."
    )

corrected = original.replace(anchor, replacement, 1)

# Verify syntax before saving anything.
compile(corrected, str(path), "exec")

assert "**Simple Summary:**" in corrected
assert "**Detailed Structured Summary:**" in corrected
assert "## 6. Bibliography" in corrected
assert "### Abstract Quality Validation" in corrected

path.write_text(corrected, encoding="utf-8")

print("SUCCESS: Report exporter repaired from original backup.")
print("SUCCESS: Existing report sections preserved.")
