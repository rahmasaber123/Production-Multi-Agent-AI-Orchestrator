"""Centralized configuration loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── LLM providers ────────────────────────────────────────
    openai_api_key: str = ""
    groq_api_key: str = ""
    tavily_api_key: str = ""

    # ── LangSmith ────────────────────────────────────────────
    langsmith_api_key: str = ""
    langchain_tracing_v2: bool = True
    langchain_project: str = "langgraph_multiagent_prod"
    langchain_endpoint: str = "https://api.smith.langchain.com"

    # ── Ollama ───────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    use_ollama: bool = True

    # ── Database ─────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://agent_user:password@localhost:5432/multiagent"

    # ── Redis ────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── API ──────────────────────────────────────────────────
    api_secret_key: str = "dev-secret-key"
    api_rate_limit: str = "20/minute"
    cors_origins: str = "http://localhost:3000"

    # ── App ──────────────────────────────────────────────────
    log_level: str = "INFO"
    max_iterations: int = 3
    environment: str = "development"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
