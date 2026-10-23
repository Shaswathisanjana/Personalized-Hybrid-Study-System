from pathlib import Path

ui_path = Path("app/research_agent/streamlit_results.py")
report_path = Path("app/research_agent/report_exporter.py")

ui = ui_path.read_text(encoding="utf-8-sig")
report = report_path.read_text(encoding="utf-8-sig")

ui_anchor = '''    st.metric(
        "Papers Summarized",
        len(result.summaries),
    )
'''

report_anchor = '''            f"**Papers summarized:** {len(result.summaries)}",
            "",
            "---",
'''

ui_replacement = '''    st.metric(
        "Papers Accepted",
        len(result.accepted_papers),
    )

    st.metric(
        "Papers Excluded",
        len(result.excluded_papers),
    )

    st.metric(
        "Papers Summarized",
        len(result.summaries),
    )

    if result.excluded_papers:
        with st.expander(
            "Excluded Papers and Reasons",
            expanded=False,
        ):
            st.caption(
                "These papers were retrieved but excluded from "
                "detailed analysis because their available "
                "abstracts did not pass the quality checks."
            )

            for paper, quality in result.excluded_papers:
                st.markdown(f"**{paper.title}**")
                st.write("Status:", quality.status.title())
                st.write("Reason:", quality.reason)

                if paper.url:
                    st.write("Source:", paper.url)

                st.divider()
'''

report_replacement = '''            f"**Papers accepted:** {len(result.accepted_papers)}",
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
'''

report_replacement += '''        ]

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

checks = [
    (ui, ui_anchor, "Streamlit metrics"),
    (report, report_anchor, "report introduction"),
]

for content, anchor, label in checks:
    if content.count(anchor) != 1:
        raise RuntimeError(
            f"Expected {label} anchor exactly once. "
            "No changes were made."
        )

if "Excluded Papers and Reasons" in ui:
    raise RuntimeError("Streamlit integration already exists.")

if "### Abstract Quality Validation" in report:
    raise RuntimeError("Report integration already exists.")

ui_backup = Path(
    "app/research_agent/"
    "streamlit_results_before_quality_display.py.bak"
)

report_backup = Path(
    "app/research_agent/"
    "report_exporter_before_quality_display.py.bak"
)

ui_backup.write_text(ui, encoding="utf-8")
report_backup.write_text(report, encoding="utf-8")

ui = ui.replace(ui_anchor, ui_replacement, 1)
report = report.replace(report_anchor, report_replacement, 1)

ui_path.write_text(ui, encoding="utf-8")
report_path.write_text(report, encoding="utf-8")

print("SUCCESS: Streamlit quality results added.")
print("SUCCESS: Report quality section added.")
print("Both original files were backed up.")
