"""Analyze user-uploaded PDFs for topic relevance and generate a Word report.

Place this module in the project's src/ directory as uploaded_pdf_analysis.py.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import OUTPUT_DIR
# from src.research_agent import ResearchAgent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.arxiv_search import get_cached_embedder
from src.analysis import build_evidence_clusters
from src.text_processing import extract_candidate_sentences

try:
    import pymupdf  # PyMuPDF
except ImportError:
    pymupdf = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None


MAX_PDF_COUNT = 15
MAX_PDF_SIZE_BYTES = 30 * 1024 * 1024


def _read_pdf(uploaded_file) -> tuple[str, list[dict[str, Any]], str | None]:
    """Extract page text and metadata from an uploaded PDF in memory."""
    raw = uploaded_file.getvalue()
    if not raw.startswith(b"%PDF"):
        raise ValueError("The uploaded file does not appear to be a valid PDF.")

    pages: list[dict[str, Any]] = []
    metadata_title = ""

    if pymupdf is not None:
        with pymupdf.open(stream=raw, filetype="pdf") as document:
            metadata_title = ((document.metadata or {}).get("title") or "").strip()
            for index, page in enumerate(document):
                pages.append({"page": index + 1, "text": page.get_text("text") or ""})
    elif PdfReader is not None:
        import io
        reader = PdfReader(io.BytesIO(raw))
        metadata_title = str((reader.metadata or {}).get("/Title") or "").strip()
        for index, page in enumerate(reader.pages):
            pages.append({"page": index + 1, "text": page.extract_text() or ""})
    else:
        raise RuntimeError("PDF extraction requires PyMuPDF or pypdf. Install with: pip install pymupdf pypdf")

    full_text = "\n\n".join(page["text"] for page in pages).strip()
    return full_text, pages, metadata_title or None


def _is_probable_title(line: str) -> bool:
    """Reject common running headers, venue names, and document-template text."""
    low = line.lower()
    bad_phrases = (
        "journal of latex class files", "ieee transactions on", "proceedings of the",
        "international journal of", "vol.", "volume ", "issue ", "copyright",
        "all rights reserved", "arxiv preprint", "arxiv.org", "doi.org",
        "received:", "accepted:", "published:", "issn", "www.",
    )
    if any(phrase in low for phrase in bad_phrases):
        return False
    if re.match(r"^(\d{1,4}[.)]?\s*)?(abstract|keywords|index terms|introduction|contents)\b", low):
        return False
    if line.count("|") >= 2 or line.count("_") >= 3:
        return False
    return True


def _guess_title(metadata_title: str | None, full_text: str, filename: str) -> str:
    if metadata_title and len(metadata_title.strip()) >= 5:
        cleaned = re.sub(r"\s+", " ", metadata_title).strip()
        if cleaned.lower() not in {"untitled", "microsoft word", "document"} and _is_probable_title(cleaned):
            return cleaned[:250]

    # Paper titles are commonly near the top of page one. Skip venue/running headers
    # instead of accepting the first long line, which caused false titles in some PDFs.
    candidates = []
    for line in (full_text.splitlines()[:45] if full_text else []):
        line = re.sub(r"\s+", " ", line).strip(" \t-|•")
        if not (15 <= len(line) <= 240) or not _is_probable_title(line):
            continue
        if "@" in line or "http" in line.lower() or line.count(".") > 3:
            continue
        words = line.split()
        alpha = sum(ch.isalpha() for ch in line)
        if len(words) >= 4 and alpha >= 15:
            # Prefer lines that look like a title and appear early in the document.
            score = min(len(words), 18) + (3 if len(line) < 150 else 0)
            candidates.append((score, line))
    if candidates:
        return max(candidates, key=lambda item: item[0])[1][:250]
    return Path(filename).stem.replace("_", " ").replace("-", " ").strip() or "Untitled PDF"

def _extract_abstract(full_text: str) -> str:
    if not full_text:
        return ""
    match = re.search(
        r"(?is)\babstract\b\s*[:\n]?\s*(.*?)(?=\n\s*(?:1\.?\s*)?(?:introduction|keywords|index terms)\b)",
        full_text[:18000],
    )
    if match and len(match.group(1).strip()) > 80:
        return re.sub(r"\s+", " ", match.group(1)).strip()[:5000]
    # Fallback: use early body text for semantic matching, without claiming it is an abstract.
    return re.sub(r"\s+", " ", full_text[:2200]).strip()


def _topic_terms(topic: str) -> set[str]:
    stop = {"using", "with", "from", "into", "based", "approach", "system", "study", "analysis", "detection", "classification", "deep", "learning", "and", "for", "the", "of", "in", "on", "a", "an"}
    return {word for word in re.findall(r"[a-z0-9]+", topic.lower()) if len(word) > 2 and word not in stop}


def _is_pcb_topic(topic: str) -> bool:
    low = topic.lower()
    return bool(re.search(r"\b(pcb|pcbs|printed circuit boards?|printed wiring boards?)\b", low))


def _classify_relevance(topic: str, records: list[dict], threshold: float) -> list[dict]:
    """Use semantic similarity plus a topic-domain gate to avoid false inclusions."""
    if not records:
        return records
    embedder = get_cached_embedder()
    query_vector = embedder.embed_query(topic)
    texts = [
        f"Title: {item['title']}\nAbstract or opening text: {item['abstract']}\n"
        f"Additional opening context: {item.get('opening_context', '')[:2500]}"
        for item in records
    ]
    vectors = embedder.embed_documents(texts)
    scores = vectors @ query_vector
    pcb_topic = _is_pcb_topic(topic)
    pcb_pattern = re.compile(
        r"\b(pcb|pcbs|printed circuit boards?|printed wiring boards?|circuit[- ]board assembly|"
        r"surface[- ]mount components?|solder (?:joint|bridge|defect|inspection)|copper track defects?)\b",
        re.I,
    )
    generic_defect_pattern = re.compile(
        r"\b(surface defect|surface inspection|texture image|manufacturing defect|visual anomaly|"
        r"defect detection|industrial inspection|steel defect|stone texture|fabric defect)\b", re.I
    )
    topic_terms = _topic_terms(topic)

    for record, raw_score in zip(records, scores):
        score = float(raw_score)
        title = record.get("title", "")
        evidence_text = f"{title} {record.get('abstract', '')} {record.get('opening_context', '')[:2500]}"
        title_has_pcb = bool(pcb_pattern.search(title))
        body_has_pcb = bool(pcb_pattern.search(evidence_text))
        terms_in_evidence = {word for word in re.findall(r"[a-z0-9]+", evidence_text.lower()) if len(word) > 2}
        overlap = topic_terms.intersection(terms_in_evidence)
        record["relevance_score"] = round(score, 4)
        record["topic_term_overlap"] = sorted(overlap)

        # For PCB research, generic surface-defect papers are related background only;
        # they must not enter the core PCB paper comparison without PCB-specific evidence.
        if pcb_topic and not body_has_pcb:
            if generic_defect_pattern.search(evidence_text) or score >= threshold:
                record["decision"] = "Indirectly relevant — excluded from core analysis"
                record["decision_reason"] = (
                    "Discusses general surface/industrial defect detection, but the extracted title and text "
                    "do not establish a PCB-specific application. Kept as related-work background only."
                )
                record["relevance_class"] = "indirect"
            else:
                record["decision"] = "Irrelevant — excluded"
                record["decision_reason"] = "No PCB-specific evidence and semantic similarity is below the threshold."
                record["relevance_class"] = "irrelevant"
            record["included"] = False
        elif score >= threshold and (not topic_terms or len(overlap) >= 1):
            record["decision"] = "Directly relevant — included"
            record["decision_reason"] = "Semantic similarity meets the threshold and the extracted text supports the target domain."
            record["relevance_class"] = "direct"
            record["included"] = True
        elif score >= threshold - 0.05:
            record["decision"] = "Borderline — excluded pending review"
            record["decision_reason"] = "Score is close to the threshold; verify the full title, abstract, and application domain."
            record["relevance_class"] = "borderline"
            record["included"] = False
        else:
            record["decision"] = "Irrelevant — excluded"
            record["decision_reason"] = "Semantic similarity is below the configured relevance threshold."
            record["relevance_class"] = "irrelevant"
            record["included"] = False
    return records

def _append_upload_audit(docx_path: Path, topic: str, decisions: list[dict]) -> None:
    """Append a transparent uploaded-file classification table to the Word report."""
    if Document is None:
        return
    document = Document(str(docx_path))
    # The shared report template uses arXiv wording for its reference entries;
    # rewrite those labels because these records came from user-uploaded files.
    for paragraph in document.paragraphs:
        if paragraph.text.lstrip().startswith("[") and "arXiv." in paragraph.text:
            paragraph.text = paragraph.text.replace("arXiv.", "User-uploaded PDF.")
    document.add_page_break()
    document.add_heading("Appendix: Uploaded PDF relevance assessment", level=1)
    document.add_paragraph(f"User-specified topic: {topic}")
    document.add_paragraph(
        "Only directly relevant files were included in the paper-wise analysis. "
        "Relevance was estimated using BGE semantic similarity and topic-specific evidence checks. "
        "For PCB topics, generic surface-defect papers without PCB-specific evidence are excluded from the core analysis and classified as indirectly relevant. "
        "Scores are a screening aid; borderline files and poor title extractions should be reviewed."
    )
    table = document.add_table(rows=1, cols=5)
    table.style = "Table Grid"
    headers = ["Uploaded file", "Extracted title", "Similarity", "Decision", "Reason / extraction status"]
    for cell, header in zip(table.rows[0].cells, headers):
        cell.text = header
    for item in decisions:
        row = table.add_row().cells
        row[0].text = item.get("filename", "")
        row[1].text = item.get("title", "Untitled")
        row[2].text = str(item.get("relevance_score", "—"))
        row[3].text = item.get("decision", "Not assessed")
        row[4].text = item.get("decision_reason", item.get("extraction_error", ""))
    document.save(docx_path)


def _classification_only_report(topic: str, decisions: list[dict], output_path: Path) -> Path:
    if Document is None:
        raise RuntimeError("python-docx is required to generate Word reports. Install with: pip install python-docx")
    document = Document()
    document.add_heading("Uploaded PDF Relevance Report", level=0)
    document.add_paragraph(f"Topic: {topic}")
    document.add_paragraph(f"Generated: {datetime.now():%Y-%m-%d %H:%M}")
    document.add_paragraph(
        "No uploaded PDF passed the configured relevance threshold, so no paper-wise research synthesis was generated. "
        "Review the classifications or adjust the threshold and try again."
    )
    table = document.add_table(rows=1, cols=5)
    table.style = "Table Grid"
    for cell, value in zip(table.rows[0].cells, ["Uploaded file", "Extracted title", "Similarity", "Decision", "Reason"]):
        cell.text = value
    for item in decisions:
        cells = table.add_row().cells
        values = [item.get("filename", ""), item.get("title", "Untitled"), str(item.get("relevance_score", "—")), item.get("decision", "Not assessed"), item.get("decision_reason", item.get("extraction_error", ""))]
        for cell, value in zip(cells, values):
            cell.text = str(value)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(output_path)
    return output_path


def analyze_uploaded_pdfs(topic: str, uploaded_files: list, min_relevance: float = 0.30) -> dict:
    """Classify up to 15 PDFs, analyze relevant ones, and generate DOCX/JSON reports."""
    topic = (topic or "").strip()
    if not topic:
        raise ValueError("Please enter a research topic.")
    if not uploaded_files:
        raise ValueError("Upload at least one PDF.")
    if len(uploaded_files) > MAX_PDF_COUNT:
        raise ValueError(f"You can upload at most {MAX_PDF_COUNT} PDFs per run.")
    if not 0.0 <= float(min_relevance) <= 1.0:
        raise ValueError("Relevance threshold must be between 0 and 1.")

    records: list[dict] = []
    decisions: list[dict] = []
    # Validate and extract all files first. A failed extraction is reported separately
    # rather than being mislabeled as an unrelated paper.
    for index, uploaded in enumerate(uploaded_files, 1):
        filename = Path(uploaded.name).name
        size = len(uploaded.getvalue())
        decision_record = {"filename": filename, "title": Path(filename).stem, "relevance_score": None, "_order": index}
        if size > MAX_PDF_SIZE_BYTES:
            decision_record.update({
                "decision": "Not processed — file too large",
                "decision_reason": "Prototype limit is 30 MB per PDF.",
                "included": False,
            })
            decisions.append(decision_record)
            continue
        try:
            full_text, pages, metadata_title = _read_pdf(uploaded)
            if len(full_text.strip()) < 300:
                raise ValueError("Too little selectable text was extracted; the PDF may be scanned or image-only.")
            title = _guess_title(metadata_title, full_text, filename)
            abstract = _extract_abstract(full_text)
            records.append({
                "title": title,
                "abstract": abstract,
                "authors": [],
                "published": None,
                "updated": None,
                "url": f"Uploaded file: {filename}",
                "pdf_url": None,
                "filename": filename,
                "_order": index,
                "opening_context": full_text[:6000],
                "_full_text": full_text,
                "_pages": pages,
            })
        except Exception as exc:
            decision_record.update({
                "decision": "Could not assess — extraction failed",
                "decision_reason": str(exc),
                "extraction_error": str(exc),
                "included": False,
            })
            decisions.append(decision_record)

    if records:
        records = _classify_relevance(topic, records, float(min_relevance))
        for record in records:
            decisions.append({key: record.get(key) for key in (
                "filename", "title", "relevance_score", "topic_term_overlap", "relevance_class", "decision", "decision_reason", "included", "_order"
            )})

    decisions.sort(key=lambda item: item.get("_order", 10_000))
    for item in decisions:
        item.pop("_order", None)

    relevant_records = [record for record in records if record.get("included")]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    docx_path = OUTPUT_DIR / "uploaded_pdf_literature_report.docx"
    json_path = OUTPUT_DIR / "uploaded_pdf_report.json"

    if not relevant_records:
        _classification_only_report(topic, decisions, docx_path)
        report = {
            "generated_at": datetime.now().isoformat(),
            "topic": topic,
            "source": "user-uploaded PDFs",
            "relevance_threshold": float(min_relevance),
            "number_uploaded": len(uploaded_files),
            "number_relevant": 0,
            "uploaded_pdf_classification": decisions,
            "message": "No PDFs passed the relevance threshold; no paper-wise synthesis was generated.",
            "word_report_path": str(docx_path),
        }
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        return {"report": report, "decisions": decisions, "docx_path": docx_path, "json_path": json_path}

    # Initialize the research components only after at least one PDF passed the filter.
    agent = ResearchAgent()
    analyzed_papers = []
    for record in relevant_records:
        full_text = record.pop("_full_text")
        pages = record.pop("_pages")
        record["opening_context"] = record.pop("opening_context", "")
        sections = agent.pdf_section_extractor._detect_sections(full_text, pages)
        record.update({
            "full_text": full_text,
            "sections": sections,
            "full_text_extracted": True,
            "pdf_extraction_error": None,
            "pdf_path": None,
            "source_type": "user_upload",
        })
        analyzed_papers.append(record)

    paper_analyses = agent.paper_analyzer.analyze_papers(topic, analyzed_papers)

    candidates = []
    source_indices = []
    for paper_index, paper in enumerate(analyzed_papers):
        for sentence in extract_candidate_sentences(paper):
            candidates.append(sentence)
            source_indices.append(paper_index)

    evidence_clusters = []
    if candidates:
        embedder = get_cached_embedder()
        sentence_embeddings = embedder.embed_documents(candidates)
        query_embedding = embedder.embed_query(topic)
        evidence_clusters = build_evidence_clusters(candidates, sentence_embeddings, query_embedding, source_indices)
        for cluster in evidence_clusters:
            for evidence in cluster.get("evidence", []):
                paper_index = evidence.get("paper_index")
                if paper_index is not None and 0 <= paper_index < len(analyzed_papers):
                    evidence["paper_title"] = analyzed_papers[paper_index].get("title", "Unknown")
                    evidence["paper_url"] = analyzed_papers[paper_index].get("url", "")

    synthesis = agent.synthesizer.synthesize(topic, analyzed_papers, evidence_clusters) if evidence_clusters else None

    # Use the existing Word report generator and append the explicit upload decisions.
    generated_docx = agent.word_report_generator.generate(
        topic=topic,
        paper_analyses=paper_analyses,
        gap_synthesis=synthesis,
        evidence_clusters=evidence_clusters,
        output_path=docx_path,
    )
    _append_upload_audit(Path(generated_docx), topic, decisions)

    report = agent.make_report(topic, analyzed_papers, paper_analyses, evidence_clusters, synthesis)
    report.update({
        "source": "user-uploaded PDFs",
        "relevance_threshold": float(min_relevance),
        "number_uploaded": len(uploaded_files),
        "number_relevant": len(relevant_records),
        "number_indirect": sum(1 for item in decisions if item.get("relevance_class") == "indirect"),
        "uploaded_pdf_classification": decisions,
        "word_report_path": str(generated_docx),
    })
    # Exclude raw full text and page content from JSON to keep the report manageable.
    report["papers"] = [
        {key: value for key, value in paper.items() if key not in ("full_text", "sections", "opening_context")}
        for paper in analyzed_papers
    ]
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return {"report": report, "decisions": decisions, "docx_path": Path(generated_docx), "json_path": json_path}
