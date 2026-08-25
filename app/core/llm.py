"""
Centralised LLM factory.
All agents import from here — swap the model in one place.
"""
from __future__ import annotations
from langchain_google_genai import ChatGoogleGenerativeAI
from configs.settings import settings


def get_llm(temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    """Return the configured free Gemini LLM."""
    return ChatGoogleGenerativeAI(
        model=settings.PRIMARY_LLM,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=temperature,
        convert_system_message_to_human=True,  # Gemini requires this
    )
