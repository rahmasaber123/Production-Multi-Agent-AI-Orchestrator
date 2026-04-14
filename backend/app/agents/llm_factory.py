

from __future__ import annotations

import os
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def make_llm(
    provider: str,
    model: str,
    temperature: float = 0.0,
    fallback_model: str = "gpt-4o-mini",
) -> BaseChatModel:

    settings = get_settings()

    try:
        if provider == "openai":
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY not set")
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                api_key=settings.openai_api_key,
            )

        elif provider == "groq":
            if not settings.groq_api_key:
                raise ValueError("GROQ_API_KEY not set")
            return ChatGroq(
                model=model,
                temperature=temperature,
                api_key=settings.groq_api_key,
            )

        elif provider == "ollama":
            if not settings.use_ollama:
                raise ValueError("Ollama disabled in config (USE_OLLAMA=false)")
            return ChatOllama(
                model=model,
                base_url=settings.ollama_base_url,
                temperature=temperature,
            )

        else:
            raise ValueError(f"Unknown provider: {provider}")

    except Exception as exc:
        logger.warning(
            "LLM unavailable %s/%s: %s — falling back to openai/%s",
            provider, model, exc, fallback_model,
        )
        return ChatOpenAI(
            model=fallback_model,
            temperature=temperature,
            api_key=settings.openai_api_key,
        )


def get_model_info(llm: BaseChatModel) -> str:
    """Extract human-readable model name from an LLM instance."""
    if hasattr(llm, "model_name"):
        return llm.model_name
    if hasattr(llm, "model"):
        return llm.model
    return type(llm).__name__
