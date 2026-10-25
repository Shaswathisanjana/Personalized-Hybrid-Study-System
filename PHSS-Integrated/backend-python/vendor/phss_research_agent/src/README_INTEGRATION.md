# PHSS Research Report Generator — full-text PDF version

This patch updates the supplied PHSS Research Agent to analyze the **full text of arXiv PDFs**, not just abstracts.

## What changed

- `pdf_sections.py`: downloads each PDF, extracts page text with PyMuPDF (or pypdf), detects common section headings with rules, and asks Gemini to classify ambiguous/unlabeled sections only when needed. Source heading and page-range metadata are retained.
- `paper_analysis.py`: sends small batches of extracted section text to Gemini to extract methodology, datasets, reported results/metrics, author-stated limitations, future work, and cautiously stated candidate gaps. If Gemini is unavailable, section excerpts are still retained in the output instead of being discarded.
- `text_processing.py`: searches limitations, future work, results/discussion, and other extracted sections for challenge evidence, falling back to the abstract only when no section text is available.
- `research_agent.py`: runs the PDF extraction stage before analysis, preserves the original BGE clustering/gap-synthesis flow, and saves section evidence separately.
- `report_generator.py`: reports full-text evidence and explicitly notes extraction limitations.

## Install dependencies

Run in your project environment:

```powershell
pip install arxiv sentence-transformers scikit-learn numpy google-genai python-dotenv python-docx pymupdf pypdf
```

PyMuPDF is preferred; pypdf is a fallback. Keep your `GEMINI_API_KEY` in `.env`. Gemini is used for ambiguous section classification and structured extraction; rule-based extraction and raw section preservation still work if Gemini is temporarily unavailable.

## Integration

1. Back up your current files.
2. Copy the `.py` files in this patch into the same Python package directory as your existing PHSS modules. Keep your existing `__init__.py` if present.
3. From the package's parent directory, run the existing entry point, for example:

```powershell
python -m your_package.research_agent
```

Replace `your_package` with your actual package directory name. The program asks for a topic and uses up to 10 papers.

## Outputs

- `outputs/latest_report.json` — structured report and per-paper extraction status/source headings.
- `outputs/extracted_paper_sections.json` — extracted text for detected sections, including headings and page ranges.
- `outputs/papers/paper_01.pdf` etc. — cached PDFs so successful downloads do not need to be repeated.
- `outputs/research_literature_report.docx` — Word report.

## Reliability notes

- Heading detection is rule-based first; ambiguous headings/unlabeled blocks can be classified by Gemini. Section detection can still miss unusual layouts.
- PDF extraction can fail for scanned/image-only PDFs or blocked downloads. Check `full_text_extracted` and `pdf_extraction_error` for each paper.
- Reported metrics and numerical values must come from extracted text; missing information is marked `Not explicitly reported in full text`.
- Potential research gaps and novelty directions are hypotheses, not verified novelty claims. Check the cited paper and broader literature before claiming novelty.
