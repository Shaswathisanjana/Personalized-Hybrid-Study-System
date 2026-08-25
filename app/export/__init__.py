from __future__ import annotations
import logging
from app.models.report import ResearchReport
from app.export.markdown_exporter import MarkdownExporter
from app.export.docx_exporter import DocxExporter
from app.export.pdf_exporter import PDFExporter

logger = logging.getLogger(__name__)


def export_all(report: ResearchReport) -> ResearchReport:
    """Run all exporters and attach file paths to the report.

    PDF export silently degrades if GTK3/pango is not installed on Windows.
    Markdown and DOCX export are always available.
    """
    report.markdown_path = str(MarkdownExporter().export(report))
    report.docx_path     = str(DocxExporter().export(report))

    try:
        report.pdf_path = str(PDFExporter().export(report))
    except (RuntimeError, OSError) as exc:
        # WeasyPrint requires GTK3/pango; skip PDF silently on Windows without it.
        logger.warning("PDF export skipped — GTK3 not available: %s", exc)
        report.pdf_path = None

    return report
