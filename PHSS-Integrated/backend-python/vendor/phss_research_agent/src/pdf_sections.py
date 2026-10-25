"""Download arXiv PDFs and extract full text into research-paper sections.

Heading rules are applied first. Gemini is used only to classify ambiguous
section headings, not to invent content. Extracted text remains traceable to the
source paper and section heading. PDF text extraction requires PyMuPDF or pypdf.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
try:
    import pymupdf  # PyMuPDF
except ImportError:
    pymupdf = None
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None
try:
    from google import genai
except ImportError:
    genai = None

from .config import GEMINI_MODEL, OUTPUT_DIR

load_dotenv()
MISSING = "Not explicitly reported in full text"
SECTION_TYPES = ("methodology", "dataset", "results", "limitations", "future_work", "other")

# Recognize common headings; headings vary between venues and papers.
HEADING_RULES = {
    "methodology": re.compile(r"^(?:\d+(?:\.\d+)*\s+)?(?:method(?:s|ology)?|materials\s+and\s+methods|proposed\s+(?:method|approach|framework)|approach|model\s+architecture|system\s+design|implementation)(?:\s*[:.]\s*.*)?$", re.I),
    "dataset": re.compile(r"^(?:\d+(?:\.\d+)*\s+)?(?:dataset(?:s)?|data(?:set)?\s+(?:collection|description|preprocessing)|experimental\s+setup|study\s+area)(?:\s*[:.]\s*.*)?$", re.I),
    "results": re.compile(r"^(?:\d+(?:\.\d+)*\s+)?(?:results?(?:\s+and\s+discussion)?|experiments?(?:\s+and\s+results)?|experimental\s+results|evaluation|performance\s+evaluation|discussion|ablation\s+study|quantitative\s+results)(?:\s*[:.]\s*.*)?$", re.I),
    "limitations": re.compile(r"^(?:\d+(?:\.\d+)*\s+)?(?:limitations?(?:\s+and\s+threats\s+to\s+validity)?|threats\s+to\s+validity|study\s+limitations)(?:\s*[:.]\s*.*)?$", re.I),
    "future_work": re.compile(r"^(?:\d+(?:\.\d+)*\s+)?(?:future\s+work|future\s+directions|conclusion(?:s)?(?:\s+and\s+future\s+work)?|concluding\s+remarks)(?:\s*[:.]\s*.*)?$", re.I),
}
GENERIC_HEADING = re.compile(r"^(?:\d+(?:\.\d+)*\s+)?[A-Z][A-Za-z0-9 ,:()\-/]{2,90}$")


def _normalize_heading(line: str) -> str:
    line = re.sub(r"\s+", " ", line).strip()
    line = re.sub(r"\s*\.{2,}\s*\d+\s*$", "", line)
    return line.strip(" .\t")


def _extract_pdf_text(pdf_path: Path) -> tuple[str, list[dict[str, Any]]]:
    pages = []
    if pymupdf is not None:
        with pymupdf.open(pdf_path) as doc:
            for i, page in enumerate(doc):
                pages.append({"page": i + 1, "text": page.get_text("text") or ""})
    elif PdfReader is not None:
        reader = PdfReader(str(pdf_path))
        for i, page in enumerate(reader.pages):
            pages.append({"page": i + 1, "text": page.extract_text() or ""})
    else:
        raise RuntimeError("Install PyMuPDF or pypdf to extract PDF text: pip install pymupdf pypdf")
    return "\n\n".join(p["text"] for p in pages), pages


class PDFSectionExtractor:
    def __init__(self, output_dir: Path | str | None = None):
        self.output_dir = Path(output_dir or (OUTPUT_DIR / "papers"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        api_key = __import__("os").getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key and genai is not None else None

    def _cache_path(self, paper: dict) -> Path | None:
        """Return a stable extraction-cache path based on the exact PDF URL."""
        url = paper.get("pdf_url")
        if not url:
            return None
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        cache_dir = self.output_dir / "extraction_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / f"{key}.json"

    def _load_cached_extraction(self, paper: dict) -> dict | None:
        """Load only a valid successful extraction for this exact PDF URL."""
        cache_path = self._cache_path(paper)
        if cache_path is None or not cache_path.is_file():
            return None
        try:
            with cache_path.open("r", encoding="utf-8") as handle:
                cached = json.load(handle)
            if cached.get("provenance_version") != 2:
                return None
            if cached.get("pdf_url") != paper.get("pdf_url"):
                return None
            full_text = cached.get("full_text")
            sections = cached.get("sections")
            if not isinstance(full_text, str) or len(full_text.strip()) < 500:
                return None
            if not isinstance(sections, dict):
                return None
            from .provenance import validate_pdf_identity
            validate_pdf_identity(paper,full_text)
            return {"full_text": full_text, "sections": sections}
        except (OSError, ValueError, TypeError):
            return None

    def _save_cached_extraction(self, paper: dict, full_text: str, sections: dict) -> None:
        """Atomically cache successful extraction results; never cache failures."""
        cache_path = self._cache_path(paper)
        if cache_path is None:
            return
        payload = {
            "provenance_version":2,
            "pdf_url": paper.get("pdf_url"),
            "full_text": full_text,
            "sections": sections,
        }
        temporary_path = cache_path.with_suffix(".tmp")
        try:
            with temporary_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False)
            temporary_path.replace(cache_path)
        except OSError as exc:
            temporary_path.unlink(missing_ok=True)
            print(f"    Warning: could not save extraction cache: {exc}")

    def extract_papers(self, papers: list[dict]) -> list[dict]:
        enriched = []
        for idx, paper in enumerate(papers, 1):
            print(f"  [{idx}/{len(papers)}] PDF: {paper.get('title', 'Untitled')}")
            record = dict(paper)
            try:
                cached = self._load_cached_extraction(paper)
                if cached is not None:
                    pdf_path = self._pdf_path_for_url(paper.get("pdf_url"))
                    record["pdf_path"] = str(pdf_path) if pdf_path.is_file() else None
                    record["full_text_extracted"] = True
                    record["sections"] = cached["sections"]
                    record["full_text"] = cached["full_text"]
                    record["pdf_extraction_error"] = None
                    print("    Using cached PDF text and sections.")
                else:
                    pdf_path = self._download_pdf(paper, idx)
                    full_text, pages = _extract_pdf_text(pdf_path)
                    if len(full_text.strip()) < 500:
                        raise RuntimeError("PDF text is too short; it may be scanned or extraction failed")
                    from .provenance import validate_pdf_identity
                    validate_pdf_identity(paper,full_text)
                    sections = self._detect_sections(full_text, pages)
                    if self.client and (not sections["methodology"] or not sections["results"] or not sections["limitations"]):
                        sections = self._llm_classify_ambiguous_sections(sections)
                    record["pdf_path"] = str(pdf_path)
                    record["full_text_extracted"] = True
                    record["sections"] = sections
                    record["full_text"] = full_text
                    record["pdf_extraction_error"] = None
                    self._save_cached_extraction(paper, full_text, sections)
            except Exception as exc:
                record["full_text_extracted"] = False
                record["sections"] = {k: [] for k in SECTION_TYPES}
                record["full_text"] = ""
                record["pdf_extraction_error"] = str(exc)
                print(f"    PDF extraction failed: {exc}")
            enriched.append(record)
        return enriched

    def _pdf_path_for_url(self, url: str) -> Path:
        """Use a URL-derived filename to prevent cross-paper index collisions."""
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        return self.output_dir / f"paper_{key}.pdf"

    def _download_pdf(self, paper: dict, index: int) -> Path:
        url = paper.get("pdf_url")
        if not url:
            raise RuntimeError("No PDF URL supplied by arXiv")
        path = self._pdf_path_for_url(url)
        if path.exists() and path.stat().st_size > 10_000:
            return path
        request = urllib.request.Request(url, headers={"User-Agent": "PHSS-Research-Agent/1.0 (academic literature review)"})
        last_error = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=45) as response, path.open("wb") as output:
                    output.write(response.read())
                if path.stat().st_size < 1_000:
                    path.unlink(missing_ok=True)
                    raise RuntimeError("Downloaded file is unexpectedly small")
                return path
            except Exception as exc:
                last_error = exc
                path.unlink(missing_ok=True)
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"PDF download failed after 3 attempts: {last_error}")

    def _detect_sections(self, full_text: str, pages: list[dict]) -> dict:
        # Preserve page markers for traceability, then detect headings line-by-line.
        lines = []
        for page in pages:
            lines.append(f"[[PAGE:{page['page']}]]")
            lines.extend((page.get("text") or "").splitlines())
        headings = []
        for i, raw_line in enumerate(lines):
            line = _normalize_heading(raw_line)
            if not line or len(line) > 110 or len(line) < 3 or line.startswith("[[PAGE:"):
                continue
            category = next((name for name, pattern in HEADING_RULES.items() if pattern.match(line)), None)
            # Generic headings are retained for LLM classification, but filter sentences and references.
            if category or (GENERIC_HEADING.match(line) and not line.endswith((",", ";")) and not re.search(r"[.!?]$", line)):
                if re.match(r"^(references|bibliography|acknowledg(?:e)?ments|appendix|supplementary material)\b", line, re.I):
                    continue
                # Likely heading: short line and either title-like or a known section name.
                if category or (len(line.split()) <= 12 and sum(c.isalpha() for c in line) >= 4):
                    headings.append({"line_index": i, "heading": line, "category": category or "other", "page": self._current_page(lines, i)})
        sections = {k: [] for k in SECTION_TYPES}
        if not headings:
            # Split unstructured text into manageable blocks so the LLM can classify content, not just the first page.
            paragraphs = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", full_text) if len(p.strip()) > 80]
            blocks, current = [], ""
            for paragraph in paragraphs:
                if current and len(current) + len(paragraph) > 2400:
                    blocks.append(current)
                    current = ""
                current = (current + "\n" + paragraph).strip()
            if current:
                blocks.append(current)
            if not blocks:
                blocks = [full_text[i:i + 2400] for i in range(0, min(len(full_text), 48000), 2400)]
            for i, block in enumerate(blocks[:24], 1):
                sections["other"].append({
                    "heading": f"Unlabeled text block {i}", "text": block,
                    "start_page": 1, "end_page": len(pages),
                })
            return sections
        for j, heading in enumerate(headings):
            start = heading["line_index"] + 1
            end = headings[j + 1]["line_index"] if j + 1 < len(headings) else len(lines)
            content = "\n".join(lines[start:end]).strip()
            content = re.sub(r"\n{3,}", "\n\n", content)
            if len(content) < 80:
                continue
            start_page = heading["page"]
            end_page = self._current_page(lines, max(start, end - 1))
            sections[heading["category"]].append({
                "heading": heading["heading"], "text": content[:30000],
                "start_page": start_page, "end_page": end_page,
            })
        return sections

    @staticmethod
    def _current_page(lines: list[str], index: int) -> int:
        page = 1
        for line in lines[:index + 1]:
            match = re.match(r"\[\[PAGE:(\d+)\]\]", line)
            if match:
                page = int(match.group(1))
        return page

    def _llm_classify_ambiguous_sections(self, sections: dict) -> dict:
        """Classify unrecognized headings and combined sections with Gemini."""
        if not self.client:
            return sections
        other = sections.get("other", [])
        if not other:
            return sections
        compact = [{"index": i, "heading": item["heading"], "text_preview": item["text"][:1400]}
                   for i, item in enumerate(other)]
        prompt = f"""Classify each supplied academic paper section by its content. Categories: methodology, dataset, results, limitations, future_work, other. A section can be assigned to one primary category only. Do not rewrite or summarize text. Return JSON only: {{\"sections\":[{{\"index\":0,\"category\":\"results\"}}]}}. Only classify from the supplied heading and preview.\nSECTIONS:\n{compact}"""
        for attempt in range(2):
            try:
                from .paper_analysis import _clean_json_response
                import json
                response = self.client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
                parsed = json.loads(_clean_json_response(response.text if response else ""))
                moves = {int(x["index"]): x["category"] for x in parsed.get("sections", [])
                         if isinstance(x, dict) and str(x.get("category", "")).lower() in SECTION_TYPES}
                for i, item in enumerate(other):
                    category = moves.get(i, "other")
                    if category != "other":
                        sections[category].append(item)
                sections["other"] = [item for i, item in enumerate(other) if moves.get(i, "other") == "other"]
                return sections
            except Exception as exc:
                print(f"    Ambiguous section classification attempt {attempt + 1} failed: {exc}")
                if attempt == 0:
                    time.sleep(2)
        return sections
