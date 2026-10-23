"""Worker entry point; never imports provider clients or writes student storage."""
import json
from pathlib import Path
import sys


def extract(source, limits):
    sys.path.append(str(Path(__file__).resolve().parents[2] / '.venv/Lib/site-packages'))
    outcome = dict(status='rejected', metadata={}, chunks=[], warnings=[])
    try:
        from app.research_agent.pdf_worker_limits import limit_memory
        limit_memory(limits['max_worker_memory_mb'])
        from pypdf import PdfReader
        reader = PdfReader(source, strict=False)
        if reader.is_encrypted:
            outcome['warnings'].append('Encrypted PDF: upload an unencrypted copy. Passwords are not stored.')
            return outcome
        if len(reader.pages) > limits['max_pages']:
            outcome['warnings'].append('PDF exceeds the configured page limit; it was not analyzed.')
            return outcome
        metadata = reader.metadata or {}
        # PDF metadata is reported as supplied, not inferred from the filename.
        outcome['metadata'] = dict(title=str(metadata.get('/Title') or '').strip()[:1000] or None,
                                   author=str(metadata.get('/Author') or '').strip()[:2000] or None,
                                   publication_details=None, year=None)
        total, blank = 0, 0
        for number, page in enumerate(reader.pages, 1):
            text = (page.extract_text() or '').strip()
            if not text:
                blank += 1
            total += len(text)
            if total > limits['max_text_chars']:
                outcome['chunks'] = []
                outcome['warnings'].append('Extracted text exceeds the configured limit; no partial full-text claim is made.')
                return outcome
            width = limits['chunk_chars']
            for start in range(0, len(text), width):
                outcome['chunks'].append(dict(chunk_id=f'p{number}-c{start // width + 1}',
                                               page=number, start_char=start,
                                               end_char=min(start + width, len(text)),
                                               text=text[start:start + width]))
        outcome['page_count'], outcome['text_chars'] = len(reader.pages), total
        if total < limits['min_text_chars']:
            outcome['warnings'].append('Scanned or text-poor PDF. OCR is unavailable; no text was invented.')
            return outcome
        if blank:
            outcome['warnings'].append(f'{blank} page(s) have no extractable text. OCR is unavailable; coverage is incomplete.')
        outcome['status'] = 'ready'
    except (MemoryError, OSError):
        outcome['status'] = 'extraction_error'
        outcome['chunks'] = []
        outcome['warnings'].append('PDF worker memory/resource limit failed or was reached. Explicit retry is available.')
    except Exception:
        outcome['chunks'] = []
        outcome['warnings'].append('Corrupt or unsupported PDF: extraction could not complete.')
    return outcome


if __name__ == '__main__':
    source, target, raw_limits = sys.argv[1:]
    Path(target).write_text(json.dumps(extract(source, json.loads(raw_limits))), encoding='utf-8')
