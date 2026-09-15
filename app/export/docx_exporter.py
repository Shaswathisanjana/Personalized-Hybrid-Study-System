from __future__ import annotations
from pathlib import Path
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from app.models.report import ResearchReport
from configs.settings import settings

HEADING_COLOR  = RGBColor(0x1A, 0x56, 0x7E)
TABLE_HDR_CLR  = RGBColor(0x1A, 0x56, 0x7E)


class DocxExporter:
    def export(self, report: ResearchReport) -> Path:
        doc = Document()
        doc.styles["Normal"].font.name = "Times New Roman"
        doc.styles["Normal"].font.size = Pt(12)

        self._cover(doc, report)

        # Sections — skip if empty
        numbered_sections = [
            ("1. Introduction",         report.introduction),
            ("2. Literature Review",    report.literature_review),
            ("3. Comparative Analysis", report.comparative_analysis),
            ("4. Research Gaps",        report.research_gaps),
            ("5. Future Directions",    report.future_directions),
        ]

        # Insert comparison table section between Literature Review and Comparative Analysis
        section_num = 2
        for heading, body in numbered_sections:
            if not (body or "").strip():
                continue  # skip empty sections

            h = doc.add_heading(heading, level=1)
            h.runs[0].font.color.rgb = HEADING_COLOR

            for para in (body or "").split("\n\n"):
                if para.strip():
                    doc.add_paragraph(para.strip())
            doc.add_paragraph()

            # After literature review, insert the comparison table if present
            if heading == "2. Literature Review" and report.paper_comparison_table:
                self._add_table_section(doc, report.paper_comparison_table)

        if report.citations:
            doc.add_heading("References", level=1)
            for i, ref in enumerate(report.citations.ieee, 1):
                p = doc.add_paragraph(f"[{i}] {ref}")
                p.style.font.size = Pt(10)

        output_dir = Path(settings.EXPORT_DIR).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"report_{report.report_id}.docx"
        doc.save(str(path))
        return path

    def _add_table_section(self, doc: Document, md_table: str) -> None:
        """Parse a markdown table and render it as a DOCX table."""
        h = doc.add_heading("3. Paper Comparison Table", level=1)
        h.runs[0].font.color.rgb = HEADING_COLOR

        lines = [line.strip() for line in md_table.strip().splitlines() if line.strip()]
        # Filter out separator lines (---|---|...)
        data_lines = [l for l in lines if not all(c in "-|: " for c in l)]

        if not data_lines:
            return

        rows_data = []
        for line in data_lines:
            # Strip leading/trailing pipes, split on |
            cells = [c.strip() for c in line.strip("|").split("|")]
            rows_data.append(cells)

        if not rows_data:
            return

        n_cols = len(rows_data[0])
        table = doc.add_table(rows=len(rows_data), cols=n_cols)
        table.style = "Table Grid"

        for r_idx, row_data in enumerate(rows_data):
            row = table.rows[r_idx]
            for c_idx, cell_text in enumerate(row_data[:n_cols]):
                cell = row.cells[c_idx]
                cell.text = cell_text
                run = cell.paragraphs[0].runs
                if run:
                    run[0].font.size = Pt(8)
                # Header row styling
                if r_idx == 0:
                    from docx.oxml.ns import qn
                    from docx.oxml import OxmlElement
                    tc_pr = cell._tc.get_or_add_tcPr()
                    shd = OxmlElement("w:shd")
                    shd.set(qn("w:val"), "clear")
                    shd.set(qn("w:color"), "auto")
                    shd.set(qn("w:fill"), "1A567E")
                    tc_pr.append(shd)
                    if run:
                        run[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                        run[0].font.bold = True

        doc.add_paragraph()

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
        tp2 = doc.add_paragraph()
        tp2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        tp2.add_run(f"Topic: {report.topic}").font.size = Pt(11)
        doc.add_page_break()
