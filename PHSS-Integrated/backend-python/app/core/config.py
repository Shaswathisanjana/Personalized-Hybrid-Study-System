"""Environment settings for the PHSS Python AI service."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Use this service's explicit environment file, not an incidental ancestor .env.
from pathlib import Path
load_dotenv(Path(__file__).resolve().parents[2] / '.env', override=True)
canonical_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
if canonical_key:
    os.environ["GEMINI_API_KEY"] = canonical_key
    os.environ["GOOGLE_API_KEY"] = canonical_key

@dataclass(frozen=True)
class Settings:
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/ai_tutor")
    service_key: str = os.getenv("PHSS_SERVICE_KEY", "")
    database_name: str = os.getenv("MONGO_DATABASE", "ai_tutor")
    host: str = os.getenv("AI_HOST", "127.0.0.1")
    port: int = int(os.getenv("AI_PORT", "8000"))
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    max_research_results: int = int(os.getenv("MAX_RESEARCH_RESULTS", "10"))

settings = Settings()
