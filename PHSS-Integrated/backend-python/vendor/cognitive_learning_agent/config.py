"""Configuration settings for Cognitive Learning Agent."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for this module
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    # LLM Settings
    GROQ_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    DEFAULT_GROQ_MODEL: str = "openai/gpt-oss-20b"
    DEFAULT_GEMINI_MODEL: str = "gemini-2.5-flash"
    PREFER_PROVIDER: str = "groq"  # "groq", "gemini", or "heuristic"

    # Database Settings
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'cognitive_memory.db'}"

    # Embeddings / Vector Database
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-base-en-v1.5"
    FALLBACK_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    USE_VECTOR_DB: bool = True
    CHROMA_PERSIST_DIR: str = str(BASE_DIR / "chroma_store")

    # Search & Discovery Settings
    MAX_SEARCH_RESULTS_PER_QUERY: int = 6
    SEARCH_TIMEOUT_SECONDS: int = 8
    LINK_VALIDATION_TIMEOUT: int = 5
    MAX_VALIDATION_WORKERS: int = 8

    # Cognitive Engine Thresholds
    PROFICIENCY_THRESHOLD: float = 0.70
    MASTERY_THRESHOLD: float = 0.88
    MIN_EVIDENCE_FOR_MASTERY: int = 3
    DEFAULT_CONFIDENCE_DECAY: float = 0.05
    CONFLICT_CONFIDENCE_PENALTY: float = 0.25

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
