"""Resolve existing local dependencies without installing or changing them."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def prepare_imports():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    local = ROOT / '.venv' / 'Lib' / 'site-packages'
    if local.is_dir() and str(local) not in sys.path:
        sys.path.append(str(local))


def dependency_errors():
    import importlib
    errors = []
    for name in ('streamlit', 'google.genai', 'dotenv', 'pypdf', 'docx'):
        try:
            importlib.import_module(name)
        except (ImportError, OSError):
            errors.append(name)
    return errors
