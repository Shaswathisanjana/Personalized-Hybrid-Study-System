from __future__ import annotations
import io
import logging

import httpx

logger = logging.getLogger(__name__)


async def parse_pdf_with_fallback(paper) -> tuple[str, float]:
    """
    Returns (text, confidence).
    confidence = 1.0 → full PDF parsed
    confidence = 0.3 → abstract-only
    """
    if paper.pdf_url:
        try:
            text = await _download_and_extract(str(paper.pdf_url))
            if text and len(text.strip()) > 500:
                return text, 1.0
        except Exception as e:
            logger.warning(f"PDF parse failed for {paper.paper_id}: {e}")

    return paper.abstract or "", 0.3


async def _download_and_extract(pdf_url: str) -> str:
    # 5s connect, 12s read — falls back to abstract quickly if PDF is slow/unreachable
    timeout = httpx.Timeout(timeout=12.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(pdf_url)
        resp.raise_for_status()

    # Try PyMuPDF first
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=resp.content, filetype="pdf")
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text
    except Exception:
        pass

    # Fallback: pdfplumber
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
            text = "\n".join(
                page.extract_text() or "" for page in pdf.pages
            )
        return text
    except Exception as e:
        raise RuntimeError(f"Both PDF parsers failed: {e}") from e
