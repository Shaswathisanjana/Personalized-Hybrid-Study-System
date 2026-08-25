from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ── FREE LLM: Google Gemini ──────────────────────────────────────────
    # Get your free key at: https://aistudio.google.com/app/apikey
    # Free tier: 1,500 requests/day, 15 requests/minute — no credit card
    GOOGLE_API_KEY: str = ""

    # Leave blank — only needed if you also want OpenAI as a backup
    OPENAI_API_KEY: str = ""

    # ── Research APIs (all free, no signup needed) ───────────────────────
    SEMANTIC_SCHOLAR_API_KEY: str = ""        # optional, just gives higher rate limits
    CROSSREF_MAILTO: str = "phss@example.com" # your email (no signup, just politeness header)

    # ── Embeddings (local sentence-transformers, completely free) ─────────
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"   # downloaded once (~22 MB), runs offline

    # ── LLM model names ───────────────────────────────────────────────────
    PRIMARY_LLM: str  = "gemini-3.6-flash"        # free via Google AI Studio (new accounts)
    FALLBACK_LLM: str = "gemini-3.5-flash-lite"   # lite fallback for new accounts

    # ── ChromaDB — local embedded (no server needed) ──────────────────────
    CHROMA_PERSIST_DIR: str = "./data/chroma"

    # ── Export ────────────────────────────────────────────────────────────
    EXPORT_DIR: str      = "./data/exports"
    PAPER_CACHE_DIR: str = "./data/papers"

    # ── App ───────────────────────────────────────────────────────────────
    APP_ENV: str            = "development"
    LOG_LEVEL: str          = "INFO"
    MAX_PAPERS_PER_SEARCH: int = 3


settings = Settings()
