"""Application configuration."""
from functools import lru_cache
from pathlib import Path
from typing import Any, List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_ROOT / ".env"

class Settings(BaseSettings):
    """Configuration loaded from environment variables."""
    # App Info
    APP_NAME: str = "MARA - Multi-Agent Research Assistant"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # CORS
    BACKEND_CORS_ORIGINS: Any = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://*.vercel.app",
        "https://*.onrender.com"
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str) and v.strip() != "":
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return [
            "http://localhost:5173",
            "http://localhost:3000",
            "https://*.vercel.app",
            "https://*.onrender.com"
        ]

    # LLM Configuration
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL: str = "deepseek/deepseek-v4-flash"
    MODEL_TEMPERATURE: float = 0.5
    MAX_TOKENS: int = 2000
    TIMEOUT: int = 60
    MAX_RETRIES: int = 3

    # Research Tools
    TAVILY_API_KEY: str | None = None

    # Workflow behavior
    ENABLE_HUMAN_REVIEW: bool = False
    HISTORY_LIMIT: int = 100

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()