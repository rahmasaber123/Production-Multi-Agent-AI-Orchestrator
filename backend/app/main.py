"""FastAPI application — multi-agent LLM orchestrator."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router as v1_router
from app.core.config import get_settings
from app.core.database import close_db, init_db
from app.core.logging import get_logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle."""
    setup_logging()
    logger = get_logger("app")
    logger.info("Starting Multi-Agent Orchestrator")

    settings = get_settings()

    # Push keys into os.environ for LangChain/LangSmith
    import os
    for key in (
        "OPENAI_API_KEY", "GROQ_API_KEY", "TAVILY_API_KEY",
        "LANGSMITH_API_KEY", "LANGCHAIN_TRACING_V2",
        "LANGCHAIN_PROJECT", "LANGCHAIN_ENDPOINT",
    ):
        val = getattr(settings, key.lower(), None)
        if val:
            os.environ[key] = str(val)

    await init_db()
    logger.info("Database initialized")

    # Pre-warm orchestrator
    from app.services.orchestrator import get_orchestration_service
    get_orchestration_service()
    logger.info("Orchestration service ready")

    yield

    await close_db()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Multi-Agent LLM Orchestrator",
    description="LangGraph-based multi-agent pipeline with OpenAI, Groq, and Ollama",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global error handler ────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger = get_logger("app")
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "type": type(exc).__name__},
    )


# ── Routes ───────────────────────────────────────────────────
app.include_router(v1_router)


@app.get("/")
async def root() -> dict:
    return {
        "service": "Multi-Agent LLM Orchestrator",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
