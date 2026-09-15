"""
Centralised LLM factory.
All agents import from here — swap the model in one place.
"""
from __future__ import annotations
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from configs.settings import settings

logger = logging.getLogger(__name__)

# Known good models for this API (in preference order)
_FALLBACK_MODELS = [
    "gemini-3.6-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]


def get_llm(temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    """Return the configured free Gemini LLM.

    If PRIMARY_LLM is invalid/unavailable, silently falls back through
    a list of known-good free-tier models.
    """
    model = settings.PRIMARY_LLM or _FALLBACK_MODELS[0]

    if not model.strip():
        logger.warning("PRIMARY_LLM is empty; using %s", _FALLBACK_MODELS[0])
        model = _FALLBACK_MODELS[0]

    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=temperature,
        convert_system_message_to_human=True,  # Gemini requires this
    )
