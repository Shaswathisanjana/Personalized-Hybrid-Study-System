from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = Path(os.getenv("PHSS_RESEARCH_OUTPUT_DIR", str(BASE_DIR / "outputs"))).resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# Temporary compatibility for modules that still import Gemini
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    GROQ_MODEL
)