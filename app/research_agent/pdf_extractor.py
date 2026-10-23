"""Bounded local PDF extraction in a disposable, timed subprocess."""
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def extract_pdf(content, limits):
    with tempfile.TemporaryDirectory(prefix='phss_pdf_') as temporary:
        source, result = Path(temporary) / 'source.pdf', Path(temporary) / 'result.json'
        source.write_bytes(content)
        try:
            child = subprocess.run([sys.executable, '-B', '-m',
                                    'app.research_agent.pdf_extractor_worker', str(source), str(result),
                                    json.dumps(asdict(limits))],
                                   cwd=Path(__file__).resolve().parents[2],
                                   capture_output=True, timeout=limits.extraction_timeout)
        except subprocess.TimeoutExpired:
            return dict(status='extraction_error', metadata={}, chunks=[],
                        warnings=['Extraction timed out. Explicit retry is available.'])
        if child.returncode or not result.is_file():
            return dict(status='extraction_error', metadata={}, chunks=[],
                        warnings=['Extraction worker failed. Explicit retry is available.'])
        return json.loads(result.read_text(encoding='utf-8'))
