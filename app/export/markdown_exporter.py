from __future__ import annotations
from pathlib import Path
from app.models.report import ResearchReport
from configs.settings import settings


class MarkdownExporter:
    def export(self, report: ResearchReport) -> Path:
        # Resolve to absolute so paths work regardless of Streamlit's CWD
        output_dir = Path(settings.EXPORT_DIR).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"report_{report.report_id}.md"
        content = self._frontmatter(report) + report.full_markdown
        path.write_text(content, encoding="utf-8")
        return path

    def _frontmatter(self, report: ResearchReport) -> str:
        return (
            f"---\ntitle: \"{report.title}\"\n"
            f"date: {report.generated_at.strftime('%Y-%m-%d')}\n"
            f"topic: \"{report.topic}\"\nreport_id: \"{report.report_id}\"\n---\n\n"
        )
