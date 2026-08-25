from __future__ import annotations
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from app.models.report import ResearchReport
from configs.settings import settings

HEADING_COLOR = RGBColor(0x1A, 0x56, 0x7E)


class DocxExporter:
    def export(self, report: ResearchReport) -> Path:
        doc = Document()
        doc.styles["Normal"].font.name = "Times New Roman"
        doc.styles["Normal"].font.size = Pt(12)

        self._cover(doc, report)

        for heading, body in [
            ("Abstract",                report.abstract),
            ("1. Introduction",         report.introduction),
            ("2. Literature Review",    report.literature_review),
            ("3. Comparative Analysis", report.comparative_analysis),
            ("4. Research Gaps",        report.research_gaps),
            ("5. Future Directions",    report.future_directions),
        ]:
            h = doc.add_heading(heading, level=1)
            h.runs[0].font.color.rgb = HEADING_COLOR
            for para in (body or "").split("\n\n"):
                if para.strip():
                    doc.add_paragraph(para.strip())
            doc.add_paragraph()

        if report.citations:
            doc.add_heading("References", level=1)
            for i, ref in enumerate(report.citations.ieee, 1):
                p = doc.add_paragraph(f"[{i}] {ref}")
                p.style.font.size = Pt(10)

        output_dir = Path(settings.EXPORT_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"report_{report.report_id}.docx"
        doc.save(str(path))
        return path

    def _cover(self, doc: Document, report: ResearchReport) -> None:
        doc.add_paragraph()
        tp = doc.add_paragraph()
        tp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = tp.add_run(report.title)
        run.font.size = Pt(22)
        run.font.bold = True
        run.font.color.rgb = HEADING_COLOR
        dp = doc.add_paragraph()
        dp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        dp.add_run(f"Generated: {report.generated_at.strftime('%B %d, %Y')}").font.size = Pt(11)
        doc.add_page_break()
