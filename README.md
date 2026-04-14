# Multi-Agent LLM Orchestrator

A production-ready full-stack application that orchestrates multiple AI agents (Planner, Researcher, Writer, Critic, Finalizer) across multiple LLM providers (OpenAI, Groq, Ollama) using LangGraph.

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────────────────┐
│  Next.js UI  │────▶│  FastAPI Backend                             │
│  (Port 3000) │◀────│  (Port 8000)                                 │
└─────────────┘     │                                              │
                    │  ┌──────────────────────────────────────┐    │
                    │  │  LangGraph Orchestration              │    │
                    │  │                                        │    │
                    │  │  Planner (OpenAI) ──▶ Researcher (Groq)│   │
                    │  │       ──▶ Writer (Ollama) ──▶ Critic   │   │
                    │  │       ──▶ Finalizer (OpenAI GPT-4o)    │   │
                    │  └──────────────────────────────────────┘    │
                    └──────────────────────────────────────────────┘
                          │              │             │
                    ┌─────┴─────┐  ┌────┴────┐  ┌────┴────┐
                    │ PostgreSQL │  │  Redis   │  │ Tavily  │
                    │ (Port 5432)│  │ (6379)   │  │   API   │
                    └───────────┘  └─────────┘  └─────────┘
```

## Quick Start

```bash
# 1. Copy environment file and add your API keys
cp .env.example .env

# 2. Build and run
docker-compose up 

# 3. Open the UI
open http://localhost:3000
Should a startup use open-source LLMs or closed models in 2026? Consider cost, speed, privacy, and reliability.
```

## API Keys Required

| Key | Required | Provider |
|-----|----------|----------|
| `OPENAI_API_KEY` | Yes | https://platform.openai.com |
| `GROQ_API_KEY` | Recommended | https://console.groq.com |
| `TAVILY_API_KEY` | Recommended | https://tavily.com |
| `LANGSMITH_API_KEY` | Optional | https://smith.langchain.com |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/generate` | Submit a query for multi-agent processing |
| `GET` | `/api/v1/generate/{task_id}/stream` | SSE stream of agent progress |
| `GET` | `/api/v1/tasks/{task_id}` | Get task result |
| `GET` | `/api/v1/health` | Health check |

## Development

```bash
# Backend only
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# Frontend only (any static server works)
cd frontend && python -m http.server 3000
```

## Agent Pipeline

1. **Planner** (OpenAI gpt-4o-mini) — Creates structured execution plan
2. **Researcher** (Groq Llama-3.3-70B) — Web search + knowledge synthesis
3. **Writer** (Ollama local / fallback gpt-4o-mini) — Drafts long-form response
4. **Critic** (Groq Llama-3.3-70B) — Scores and critiques the draft
5. **Finalizer** (OpenAI gpt-4o) — Produces polished final output
