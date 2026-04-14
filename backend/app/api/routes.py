"""API v1 routes — generate, stream, task retrieval, health."""

from __future__ import annotations

import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import rate_limit, verify_token
from app.models.schemas import (
    AgentEvent,
    GenerateRequest,
    HealthResponse,
    TaskResponse,
)
from app.services.orchestrator import get_orchestration_service
from app.services.task_service import TaskService

logger = get_logger("api.v1")

router = APIRouter(prefix="/api/v1", tags=["v1"])


# ══════════════════════════════════════════════════════════════
# POST /generate — submit a query
# ══════════════════════════════════════════════════════════════


@router.post(
    "/generate",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_token), Depends(rate_limit)],
)
async def generate(
    body: GenerateRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Submit a query for multi-agent processing. Returns a task_id for polling/streaming."""
    logger.info("New generate request: %s", body.query[:80])
    service = TaskService(db)
    task_id = await service.create_task(
        question=body.query,
        max_iterations=body.max_iterations,
        human_feedback=body.human_feedback,
    )
    return {
        "task_id": task_id,
        "status": "pending",
        "stream_url": f"/api/v1/generate/{task_id}/stream",
    }


# ══════════════════════════════════════════════════════════════
# GET /generate/{task_id}/stream — SSE event stream
# ══════════════════════════════════════════════════════════════


async def _event_generator(task_id: str) -> AsyncGenerator[str, None]:
    """Yield SSE-formatted events from the task pipeline."""
    async for event in TaskService.stream_events(task_id):
        data = event.model_dump_json()
        yield f"data: {data}\n\n"
    yield "data: {\"status\": \"done\"}\n\n"


@router.get(
    "/generate/{task_id}/stream",
    dependencies=[Depends(verify_token)],
)
async def stream_events(task_id: str) -> StreamingResponse:
    """Server-Sent Events stream of agent progress for a given task."""
    return StreamingResponse(
        _event_generator(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ══════════════════════════════════════════════════════════════
# GET /tasks/{task_id} — retrieve result
# ══════════════════════════════════════════════════════════════


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    dependencies=[Depends(verify_token)],
)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Retrieve a completed or in-progress task."""
    service = TaskService(db)
    task = await service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


# ══════════════════════════════════════════════════════════════
# POST /generate/sync — synchronous single-shot (no streaming)
# ══════════════════════════════════════════════════════════════


@router.post(
    "/generate/sync",
    response_model=dict,
    dependencies=[Depends(verify_token), Depends(rate_limit)],
)
async def generate_sync(body: GenerateRequest) -> dict:
    """Run the full pipeline synchronously and return the result directly."""
    orchestrator = get_orchestration_service()
    result = await orchestrator.run(
        question=body.query,
        max_iterations=body.max_iterations,
        human_feedback=body.human_feedback,
    )
    return {
        "status": "completed",
        "question": body.query,
        "plan": result.get("plan"),
        "research_notes": result.get("research_notes", []),
        "critique": result.get("critique"),
        "final_answer": result.get("draft"),
        "iterations": result.get("iteration", 0),
    }


# ══════════════════════════════════════════════════════════════
# GET /health
# ══════════════════════════════════════════════════════════════

@router.post(
    "/tasks/{task_id}/feedback",
    dependencies=[Depends(verify_token)],
)
async def post_feedback(task_id: str, body: dict) -> dict:
    """Submit human feedback to resume the pipeline."""
    from app.services.task_service import submit_feedback
    feedback = body.get("feedback", "")
    ok = await submit_feedback(task_id, feedback)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not awaiting feedback")
    return {"status": "resumed", "task_id": task_id}
@router.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    orchestrator = get_orchestration_service()
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        providers=orchestrator.get_provider_status(),
    )
