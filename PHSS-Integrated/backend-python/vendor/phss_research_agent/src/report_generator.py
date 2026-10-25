"""Generate a readable Word literature-review report for PHSS."""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any
import tempfile

from PIL import Image, ImageDraw, ImageFont

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from dotenv import load_dotenv

try:
    from groq import Groq
except ImportError:
    Groq = None

from .config import GROQ_MODEL, OUTPUT_DIR
from .paper_analysis import MISSING, _clean_json_response, _is_noisy_summary, _looks_unsupported_or_fragmentary

load_dotenv()


def _safe(value: Any, fallback=MISSING) -> str:
    if value is None:
        return fallback

    if isinstance(value, list):
        value = "; ".join(str(item) for item in value if item)

    value = re.sub(r"\s+", " ", str(value)).strip()
    return value or fallback


def _short(text: str, limit: int = 420) -> str:
    """Shorten at a sentence boundary so table cells remain readable."""
    text = re.sub(r"\s+", " ", text or "").strip()

    if len(text) <= limit:
        return text

    sentences = re.split(r"(?<=[.!?])\s+", text)
    kept = []

    for sentence in sentences:
        candidate = " ".join(kept + [sentence])

        if len(candidate) > limit:
            break

        kept.append(sentence)

    if kept:
        return " ".join(kept).strip()

    return text[:limit - 3].rsplit(" ", 1)[0].rstrip(" ,;:") + "..."


def _repeat_header(row):
    """Repeat the table header on subsequent Word pages."""
    tr_properties = row._tr.get_or_add_trPr()
    element = OxmlElement("w:tblHeader")
    element.set(qn("w:val"), "true")
    tr_properties.append(element)


def _keep_row_together(row):
    """Prevent Word from splitting a table row across pages."""
    tr_properties = row._tr.get_or_add_trPr()
    element = OxmlElement("w:cantSplit")
    tr_properties.append(element)


def _shade_cell(cell, fill="D9EAF7"):
    properties = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    properties.append(shading)


def _workflow_fallback_steps(paper: dict) -> list[str]:
    """Create conservative workflow steps from existing methodology text only."""
    methodology = re.sub(r"\s+", " ", str(paper.get("methodology") or "")).strip()
    if not methodology or methodology == MISSING:
        return []

    # Prefer explicit sentence/semicolon boundaries; do not invent stages.
    parts = re.split(r"(?<=[.!?])\s+|;\s*", methodology)
    parts = [part.strip(" \t\r\n-•") for part in parts if part.strip(" \t\r\n-•")]

    # Keep a concise sequence of statements already present in the extracted method.
    steps = []
    for part in parts:
        part = re.sub(r"^(methodology|methods?)\s*:\s*", "", part, flags=re.I).strip()
        if len(part) > 150:
            part = _short(part, 150)
        if part and part not in steps:
            steps.append(part)
        if len(steps) >= 6:
            break

    return steps if len(steps) >= 2 else []


def _load_font(size: int, bold: bool = False):
    """Load a widely available font, with a Pillow default fallback."""
    candidates = (
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
         "C:/Windows/Fonts/arialbd.ttf"]
        if bold else
        ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "C:/Windows/Fonts/arial.ttf"]
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap_label(text: str, max_chars: int = 54) -> list[str]:
    words = re.sub(r"\s+", " ", text).split()
    lines, current = [], []
    for word in words:
        candidate = " ".join(current + [word])
        if len(candidate) > max_chars and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines[:3]


def _draw_workflow_diagram(title: str, steps: list[str], output_path: Path) -> bool:
    """Render a compact vertical workflow image with Pillow."""
    if len(steps) < 2:
        return False

    width = 1200
    margin = 42
    box_width = width - margin * 2
    box_padding = 20
    font = _load_font(25)
    title_font = _load_font(30, bold=True)
    small_font = _load_font(20)
    line_height = 34
    wrapped = [_wrap_label(step) for step in steps]
    box_heights = [max(86, len(lines) * line_height + box_padding * 2) for lines in wrapped]
    header_height = 100
    arrow_gap = 54
    height = header_height + sum(box_heights) + arrow_gap * (len(steps) - 1) + 38

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_lines = _wrap_label(title, 62)
    title_y = 20
    for line in title_lines[:2]:
        draw.text((width // 2, title_y), line, fill="#1F4E79", font=title_font, anchor="mt")
        title_y += 38

    y = header_height
    for index, (lines, box_height) in enumerate(zip(wrapped, box_heights), start=1):
        x1, x2 = margin, margin + box_width
        y2 = y + box_height
        fill = "#EAF2F8" if index in (1, len(steps)) else "#F7F9FB"
        draw.rounded_rectangle((x1, y, x2, y2), radius=18, fill=fill, outline="#4F81BD", width=3)

        label_y = y + box_padding
        number = f"{index}. "
        # Draw the step number separately; label wraps within the remaining width.
        draw.text((x1 + 24, label_y + 2), number, fill="#1F4E79", font=font)
        text_x = x1 + 70
        for line in lines:
            draw.text((text_x, label_y), line, fill="#202124", font=font)
            label_y += line_height

        if index < len(steps):
            arrow_x = width // 2
            arrow_top = y2 + 7
            arrow_bottom = y2 + arrow_gap - 8
            draw.line((arrow_x, arrow_top, arrow_x, arrow_bottom), fill="#4F81BD", width=4)
            draw.polygon(
                [(arrow_x - 10, arrow_bottom - 10),
                 (arrow_x + 10, arrow_bottom - 10),
                 (arrow_x, arrow_bottom + 2)],
                fill="#4F81BD",
            )
        y = y2 + arrow_gap

    image.save(output_path, format="PNG", optimize=True)
    return True


class ReportNarrativeGenerator:
    """Generate a cross-paper narrative using Groq."""

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")

        self.client = (
            Groq(api_key=api_key)
            if api_key and Groq is not None
            else None
        )

        if api_key and Groq is None:
            print(
                "Groq SDK is unavailable. Install it using: pip install groq"
            )

    def generate(
        self,
        topic: str,
        paper_analyses: list[dict],
        gap_synthesis: str | None,
    ) -> dict:
        fallback = self._fallback(
            topic,
            paper_analyses,
            gap_synthesis,
        )

        if not self.client:
            print("Groq is unavailable. Using fallback report narrative.")
            return fallback

        compact = []

        for paper in paper_analyses:
            compact.append({
                "title": paper.get("title"),
                "year": paper.get("year"),
                "abstract": _short(
                    paper.get("abstract", ""), 1800
                ),
                "methodology": _short(
                    paper.get("methodology", ""), 450
                ),
                "dataset": _short(
                    paper.get("dataset", ""), 350
                ),
                "results_metrics": _short(
                    paper.get("results_metrics", ""), 450
                ),
                "author_stated_limitations": _short(
                    paper.get("author_stated_limitations", ""), 350
                ),
                "potential_gap": _short(
                    paper.get("potential_gap_from_evidence", ""), 350
                ),
            })

        prompt = f"""
Write a factual literature-review narrative about: {topic}

Use only the paper records supplied below. Do not add unsupported facts,
results, or numerical values.

The introduction must be a brief introduction to the topic, approximately
3-4 sentences. Base it primarily on the supplied abstracts. Explain the
topic, its importance, and broad approaches mentioned in those abstracts.

Do not describe this report, the number of papers, the extraction process,
retrieval, or the software pipeline in the introduction.

Do not list paper-by-paper results in the introduction.

Cross-paper analysis may use the extracted methodology, dataset, results,
and limitation fields. Distinguish reported findings from interpretation.

Treat research gaps as candidate directions, not verified novelty claims.
Do not claim that a method is novel merely because the supplied papers
do not mention it.

Return valid JSON only, with these three string fields:
introduction
cross_paper_analysis
potential_novelty_and_directions

Paper records:
{json.dumps(compact, ensure_ascii=False)}

Existing evidence-based gap synthesis:
{gap_synthesis or "Unavailable"}
"""

        for attempt in range(3):
            try:
                response = self.client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a scientific literature-review "
                                "assistant. Use only supplied evidence. "
                                "Do not invent facts or numbers. Return "
                                "valid JSON only, with no Markdown fences."
                            ),
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    temperature=0.1,
                    max_tokens=2500,
                    response_format={"type": "json_object"},
                )

                response_text = (
                    response.choices[0].message.content or ""
                )

                parsed = json.loads(
                    _clean_json_response(response_text)
                )

                if isinstance(parsed, dict):
                    return {
                        key: _safe(parsed.get(key), fallback[key])
                        for key in fallback
                    }

                raise ValueError(
                    "Groq response was not a JSON object."
                )

            except Exception as exc:
                print(
                    f"Groq report generation attempt "
                    f"{attempt + 1} failed: {exc}"
                )

                if attempt < 2:
                    time.sleep(2 * (attempt + 1))

        print("Using fallback report narrative.")
        return fallback


    def generate_workflows(self, paper_analyses: list[dict]) -> list[dict]:
        """Generate all paper workflows in one batched LLM request; fall back to extracted methods."""
        fallback = []
        for index, paper in enumerate(paper_analyses, start=1):
            steps = _workflow_fallback_steps(paper)
            fallback.append({
                "paper_index": paper.get("paper_index", index),
                "title": paper.get("title", "Untitled"),
                "steps": steps,
                "source_note": (
                    "Built from the extracted methodology text."
                    if steps else
                    "Insufficient methodology detail was available to create a reliable workflow."
                ),
            })

        if not self.client or not paper_analyses:
            return fallback

        compact = []
        for index, paper in enumerate(paper_analyses, start=1):
            methodology = str(paper.get("methodology") or "").strip()
            compact.append({
                "paper_index": paper.get("paper_index", index),
                "title": paper.get("title", "Untitled"),
                "abstract": _short(str(paper.get("abstract") or ""), 700),
                "methodology": _short(methodology, 1200),
            })

        prompt = f"""
Create one methodology/workflow sequence for each supplied scientific paper.
Use ONLY the supplied abstract and extracted methodology. Do not add stages,
models, preprocessing, datasets, outputs, or evaluation steps unless supported
by the supplied text. Preserve the paper's actual order when it is stated.

For original research, describe the model or method from input/data through
the main processing/model stages to output/evaluation only when those stages
are supported. For review/survey papers, diagram the review process or synthesis
approach described in the text, not a hypothetical prediction model.
If there is not enough information for at least two supported steps, return
an empty steps list for that paper. Keep each step concise (ideally under 90
characters), and return 2-7 steps maximum.

Return valid JSON only in this format:
{{"workflows":[{{"paper_index":1,"title":"paper title","steps":["step 1","step 2"]}}]}}

Paper records:
{json.dumps(compact, ensure_ascii=False)}
"""
        try:
            response = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You create source-grounded scientific methodology "
                            "diagrams. Never infer missing pipeline stages. "
                            "Return valid JSON only."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=3000,
                response_format={"type": "json_object"},
            )
            parsed = json.loads(_clean_json_response(
                response.choices[0].message.content or ""
            ))
            generated = parsed.get("workflows", []) if isinstance(parsed, dict) else []
            by_index = {}
            for item in generated:
                if not isinstance(item, dict):
                    continue
                try:
                    key = int(item.get("paper_index"))
                except (TypeError, ValueError):
                    continue
                steps = item.get("steps", [])
                if isinstance(steps, list):
                    clean_steps = []
                    for step in steps:
                        clean = re.sub(r"\s+", " ", str(step)).strip()
                        if clean and clean not in clean_steps:
                            clean_steps.append(_short(clean, 110))
                    by_index[key] = clean_steps[:7] if len(clean_steps) >= 2 else []

            for i, item in enumerate(fallback, start=1):
                key = int(item["paper_index"]) if str(item["paper_index"]).isdigit() else i
                if key in by_index:
                    item["steps"] = by_index[key]
                    item["source_note"] = (
                        "Workflow generated from the paper's extracted methodology and abstract."
                        if item["steps"] else
                        "Insufficient source detail was available to create a reliable workflow."
                    )
            return fallback
        except Exception as exc:
            print(f"Workflow generation failed; using extracted methodology only: {exc}")
            return fallback

    @staticmethod
    def _fallback(
        topic: str,
        papers: list[dict],
        gap_synthesis: str | None,
    ) -> dict:
        """Build a source-grounded narrative without an LLM."""

        fields = (
            "methodology",
            "dataset",
            "results_metrics",
            "author_stated_limitations",
        )

        counts = {
            field: sum(
                bool(paper.get(field))
                and paper.get(field) != MISSING
                for paper in papers
            )
            for field in fields
        }

        abstract_sentences = []

        for paper in papers:
            abstract = re.sub(
                r"\s+",
                " ",
                paper.get("abstract", "") or "",
            ).strip()

            if abstract:
                for sentence in re.split(
                    r"(?<=[.!?])\s+", abstract
                ):
                    sentence = sentence.strip()

                    if len(sentence) >= 35:
                        abstract_sentences.append(sentence)

                    if len(abstract_sentences) >= 4:
                        break

            if len(abstract_sentences) >= 4:
                break

        if abstract_sentences:
            introduction = " ".join(abstract_sentences[:4])

            if len(introduction) > 950:
                introduction = _short(introduction, 950)
        else:
            introduction = (
                f"{topic} is the focus of this review. "
                "The available paper records did not contain usable "
                "abstracts, so a source-grounded topic introduction "
                "could not be prepared from the supplied material."
            )

        cross_paper_analysis = (
            f"Evidence was available for methodology in "
            f"{counts['methodology']} papers, datasets in "
            f"{counts['dataset']}, results and metrics in "
            f"{counts['results_metrics']}, and author-stated limitations "
            f"in {counts['author_stated_limitations']}. Comparisons are "
            "limited by the available extracted source text."
        )

        directions = (
            "Candidate research directions require validation against "
            "the complete papers and a broader literature search. "
            + (
                gap_synthesis.strip()
                if gap_synthesis
                else "No additional gap synthesis was available."
            )
        )

        return {
            "introduction": introduction,
            "cross_paper_analysis": cross_paper_analysis,
            "potential_novelty_and_directions": directions,
        }


class WordResearchReportGenerator:
    """Build a Word literature-review report with a comparison table."""

    def __init__(self, output_dir: Path | str = OUTPUT_DIR):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.narrative_generator = ReportNarrativeGenerator()

    def generate(
        self,
        topic: str,
        paper_analyses: list[dict],
        gap_synthesis: str | None = None,
        evidence_clusters: list[dict] | None = None,
        output_path: Path | str | None = None,
    ) -> Path:
        narrative = self.narrative_generator.generate(
            topic,
            paper_analyses,
            gap_synthesis,
        )
        paper_workflows = self.narrative_generator.generate_workflows(paper_analyses)

        document = Document()
        self._configure_document(document)

        title = document.add_heading(
            "Research Literature Review Report",
            level=0,
        )
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        subtitle = document.add_paragraph()
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER

        run = subtitle.add_run(
            f"Topic: {topic}\n"
            f"Generated: {datetime.now():%Y-%m-%d %H:%M}"
        )
        run.italic = True

        document.add_heading("Scope and evidence policy", level=1)
        document.add_paragraph(
            "This preliminary report summarizes the retrieved research "
            "papers. Table fields are based on retrieved evidence from "
            "extracted PDF text. Page tags are retained where available. "
            "Missing information may reflect extraction or section-detection "
            "limitations. Potential gaps are not verified novelty claims."
        )

        document.add_heading("1. Introduction", level=1)
        document.add_paragraph(narrative["introduction"])

        document.add_heading("2. Paper-wise comparison", level=1)
        document.add_paragraph(
            "Each row represents one paper. Cells contain concise summaries. "
            "Consult the original papers and retrieved evidence for details. "
            "Reported metric names and numerical values are preserved when "
            "supported by retrieved evidence."
        )

        headers = [
            "Paper / year",
            "Methodology",
            "Dataset",
            "Results / metrics",
            "Author-stated limitations",
            "Potential gap",
        ]

        table = document.add_table(rows=1, cols=len(headers))
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False

        widths = [
            1.35, 1.45, 1.20, 1.50, 1.50, 1.50
        ]

        header_row = table.rows[0]
        _repeat_header(header_row)
        _keep_row_together(header_row)

        for index, (cell, header) in enumerate(
            zip(header_row.cells, headers)
        ):
            cell.text = header
            cell.width = Inches(widths[index])
            cell.vertical_alignment = (
                WD_CELL_VERTICAL_ALIGNMENT.CENTER
            )
            _shade_cell(cell)

            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                paragraph.paragraph_format.space_after = Pt(0)

                for run in paragraph.runs:
                    run.bold = True
                    run.font.name = "Arial"
                    run.font.size = Pt(8)

        for paper in paper_analyses:
            paper_title = _safe(
                paper.get("title"),
                "Untitled",
            )
            year = _safe(paper.get("year"))

            citation = (
                f"{paper_title}\n"
                f"({year})\n"
                f"[{paper.get('paper_index', '?')}]"
            )

            def _table_value(key: str, fallback_key: str | None = None) -> str:
                raw = paper.get(key)
                if raw in (None, "") and fallback_key:
                    raw = paper.get(fallback_key)
                value = _safe(raw)
                # Preserve concise technical answers; reject only obvious OCR dumps.
                if value != MISSING and _is_noisy_summary(value):
                    return MISSING
                return value

            values = [
                citation,
                _table_value("methodology"),
                _table_value("dataset"),
                _table_value("results_metrics"),
                _table_value("author_stated_limitations"),
                _table_value("potential_gap_from_evidence", "potential_gap_from_abstract"),
            ]

            row = table.add_row()
            _keep_row_together(row)

            for index, (cell, value) in enumerate(
                zip(row.cells, values)
            ):
                limit = 220 if index == 0 else 520
                cell.text = _short(value, limit)
                cell.width = Inches(widths[index])
                cell.vertical_alignment = (
                    WD_CELL_VERTICAL_ALIGNMENT.TOP
                )

                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.space_after = Pt(1)
                    paragraph.paragraph_format.line_spacing = 1.0

                    for run in paragraph.runs:
                        run.font.name = "Arial"
                        run.font.size = Pt(7)

        # Preserve the existing comparison table, then append one workflow per paper.
        document.add_heading("Methodology workflow by paper", level=1)
        document.add_paragraph(
            "Each diagram summarizes the working process described in the corresponding "
            "paper's extracted methodology. Diagrams are evidence-grounded summaries, "
            "not reproductions of the authors' original architecture figures."
        )

        workflow_by_index = {}
        for workflow in paper_workflows:
            try:
                workflow_by_index[int(workflow.get("paper_index"))] = workflow
            except (TypeError, ValueError):
                continue

        with tempfile.TemporaryDirectory(prefix="phss_workflows_") as temp_dir:
            for index, paper in enumerate(paper_analyses, start=1):
                paper_index = paper.get("paper_index", index)
                try:
                    workflow = workflow_by_index.get(int(paper_index), {})
                except (TypeError, ValueError):
                    workflow = {}
                paper_title = _safe(paper.get("title"), "Untitled")
                document.add_heading(
                    f"Paper {index}: {paper_title}",
                    level=2,
                )
                steps = workflow.get("steps", []) if isinstance(workflow, dict) else []
                if len(steps) >= 2:
                    image_path = Path(temp_dir) / f"workflow_{index}.png"
                    if _draw_workflow_diagram(paper_title, steps, image_path):
                        paragraph = document.add_paragraph()
                        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        paragraph.add_run().add_picture(str(image_path), width=Inches(8.4))
                        note = workflow.get("source_note") or (
                            "Generated from the extracted methodology and abstract."
                        )
                        note_paragraph = document.add_paragraph(note)
                        note_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        for run in note_paragraph.runs:
                            run.italic = True
                            run.font.size = Pt(8)
                else:
                    note_paragraph = document.add_paragraph(
                        "Workflow not generated: the extracted methodology does not contain "
                        "enough supported detail to show at least two reliable steps."
                    )
                    for run in note_paragraph.runs:
                        run.italic = True
                        run.font.size = Pt(9)

        document.add_heading("3. Cross-paper analysis", level=1)
        document.add_paragraph(
            narrative["cross_paper_analysis"]
        )

        if evidence_clusters:
            document.add_heading(
                "Recurring evidence themes from semantic analysis",
                level=2,
            )
            document.add_paragraph(
                "Cluster priority is a heuristic score based on topic relevance and unique supporting papers across the literature."
            )

            cluster_table = document.add_table(rows=1, cols=4)
            cluster_table.alignment = WD_TABLE_ALIGNMENT.CENTER
            cluster_table.autofit = False

            cluster_headers = [
                "Cluster Theme",
                "Supporting Papers",
                "Avg. Relevance",
                "Extracted Limitation Evidence",
            ]
            cluster_widths = [1.8, 1.6, 1.1, 4.4]

            header_row = cluster_table.rows[0]
            _repeat_header(header_row)
            _keep_row_together(header_row)

            for index, (cell, header) in enumerate(zip(header_row.cells, cluster_headers)):
                cell.text = header
                cell.width = Inches(cluster_widths[index])
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                _shade_cell(cell)
                for paragraph in cell.paragraphs:
                    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    paragraph.paragraph_format.space_after = Pt(0)
                    for run in paragraph.runs:
                        run.bold = True
                        run.font.name = "Arial"
                        run.font.size = Pt(8.5)

            for cluster in evidence_clusters:
                cid = cluster.get('cluster_id', '?')
                prio = cluster.get('cluster_priority', MISSING)
                unique_p = cluster.get('unique_paper_count', 0)
                ev_count = cluster.get('evidence_count', 0)
                avg_rel = cluster.get('average_relevance', MISSING)

                ev_bullets = []
                for ev in cluster.get("evidence", [])[:4]:
                    p_title = ev.get('paper_title', 'Unknown paper')
                    sentence = ev.get('sentence', '').strip()
                    if sentence:
                        ev_bullets.append(f"• [{p_title}]: \"{sentence}\"")

                ev_text = "\n\n".join(ev_bullets) if ev_bullets else "No specific quotes extracted."

                row_cells = cluster_table.add_row().cells
                row_cells[0].text = f"Cluster {cid}\n(Priority: {prio})"
                row_cells[1].text = f"{unique_p} Unique Paper(s)\n({ev_count} quotes)"
                row_cells[2].text = f"{avg_rel}"
                row_cells[3].text = ev_text

                for i, cell in enumerate(row_cells):
                    cell.width = Inches(cluster_widths[i])
                    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
                    for p in cell.paragraphs:
                        for run in p.runs:
                            run.font.name = "Arial"
                            run.font.size = Pt(8)

        document.add_heading("4. Potential research gaps", level=1)

        if gap_synthesis:
            document.add_paragraph(gap_synthesis)
        else:
            gaps = [
                paper for paper in paper_analyses
                if paper.get("potential_gap_from_evidence")
                not in (None, "", MISSING)
            ]

            if gaps:
                document.add_paragraph(
                    "The following are candidate gaps, not validated "
                    "claims across the literature."
                )

                for paper in gaps:
                    document.add_paragraph(
                        f"{paper.get('title', 'Untitled')}: "
                        f"{paper.get('potential_gap_from_evidence')}",
                        style="List Bullet",
                    )
            else:
                document.add_paragraph(
                    "No supported cross-paper gap synthesis was "
                    "available from the extracted evidence."
                )

        document.add_heading(
            "5. Potential novelty and research directions",
            level=1,
        )
        document.add_paragraph(
            narrative["potential_novelty_and_directions"]
        )
        document.add_paragraph(
            "Candidate directions require a broader literature review "
            "and validation before any novelty claim."
        )

        document.add_heading("References", level=1)

        for index, paper in enumerate(paper_analyses, 1):
            authors = ", ".join(paper.get("authors") or [])
            authors = (
                authors or "Authors not listed in retrieved metadata"
            )

            document.add_paragraph(
                f"[{index}] {authors} "
                f"({_safe(paper.get('year'), 'n.d.')}). "
                f"{_safe(paper.get('title'), 'Untitled')}. "
                f"arXiv. {paper.get('url') or 'URL not available'}"
            )

        path = (
            Path(output_path)
            if output_path
            else self.output_dir / "research_literature_report.docx"
        )
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            document.save(path)
        except PermissionError:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = path.with_name(
                f"{path.stem}_{timestamp}{path.suffix}"
            )
            document.save(path)

        print(f"Report saved to: {path}")
        return path

    @staticmethod
    def _configure_document(document: Document) -> None:
        section = document.sections[0]
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width, section.page_height = (
            section.page_height,
            section.page_width,
        )

        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.45)
        section.right_margin = Inches(0.45)

        styles = document.styles
        styles["Normal"].font.name = "Arial"
        styles["Normal"].font.size = Pt(9)

        styles["Heading 1"].font.name = "Arial"
        styles["Heading 1"].font.color.rgb = RGBColor(31, 78, 121)
        styles["Heading 1"].font.size = Pt(15)

        styles["Heading 2"].font.name = "Arial"
        styles["Heading 2"].font.size = Pt(12)

        styles["Heading 3"].font.name = "Arial"
        styles["Heading 3"].font.size = Pt(10)
