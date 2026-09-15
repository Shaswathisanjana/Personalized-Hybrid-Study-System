from __future__ import annotations
from pathlib import Path
import markdown as md
from app.models.report import ResearchReport
from configs.settings import settings

# WeasyPrint requires GTK3/pango on Windows. Import lazily so the app
# can still start without GTK installed; only PDF export will fail.

_CSS = """
@page { margin: 2.5cm; @bottom-center { content: counter(page); font-size: 10pt; } }
body { font-family: Georgia, serif; font-size: 12pt; line-height: 1.6; color: #111; }
h1   { font-family: 'Arial', sans-serif; font-size: 20pt; color: #1a567e; page-break-before: always; }
h2   { font-family: 'Arial', sans-serif; font-size: 14pt; color: #2c7bb6; }
p    { text-align: justify; margin-bottom: 0.5em; }
table { width:100%; border-collapse:collapse; margin:1em 0; }
th,td { border:1px solid #ccc; padding:0.4em 0.6em; }
th    { background:#1a567e; color:#fff; }
hr    { border: none; border-top: 1px solid #ccc; margin: 1em 0; }
"""


class PDFExporter:
    def export(self, report: ResearchReport) -> Path:
        try:
            from weasyprint import HTML, CSS  # noqa: PLC0415
        except OSError as exc:
            raise RuntimeError(
                "PDF export requires GTK3/pango on Windows.\n"
                "Install it from: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer\n"
                "Or use Markdown / DOCX export instead."
            ) from exc

        html_body = md.markdown(
            report.full_markdown,
            extensions=["tables", "fenced_code", "toc"],
        )
        full_html = (
            f"<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>"
            f"<title>{report.title}</title></head><body>{html_body}</body></html>"
        )
        output_dir = Path(settings.EXPORT_DIR).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"report_{report.report_id}.pdf"
        HTML(string=full_html).write_pdf(str(path), stylesheets=[CSS(string=_CSS)])
        return path
