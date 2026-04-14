"""Task service — manages task lifecycle with DB persistence and background execution."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, AsyncGenerator, Dict, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.models.database import TaskRecord
from app.models.schemas import AgentEvent, TaskResponse, TaskStatus
from app.services.orchestrator import get_orchestration_service

logger = get_logger("service.tasks")

_event_queues: Dict[str, asyncio.Queue] = {}
_task_states: Dict[str, dict] = {}
_task_feedback_events: Dict[str, asyncio.Event] = {}
_task_feedback: Dict[str, str] = {}


class TaskService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._orchestrator = get_orchestration_service()

    async def create_task(
        self,
        question: str,
        max_iterations: int = 2,
        human_feedback: Optional[str] = None,
    ) -> str:
        task_id = str(uuid.uuid4())
        record = TaskRecord(
            id=task_id,
            question=question,
            status=TaskStatus.PENDING.value,
            max_iterations=max_iterations,
            human_feedback=human_feedback,
        )
        self._db.add(record)
        await self._db.flush()
        await self._db.commit()

        _event_queues[task_id] = asyncio.Queue()

        asyncio.create_task(
            _execute_pipeline(task_id, question, max_iterations, human_feedback)
        )

        logger.info("Task created: %s", task_id)
        return task_id

    async def get_task(self, task_id: str) -> Optional[TaskResponse]:
        stmt = select(TaskRecord).where(TaskRecord.id == task_id)
        result = await self._db.execute(stmt)
        record = result.scalar_one_or_none()
        if not record:
            return None
        return TaskResponse(
            task_id=str(record.id),
            status=TaskStatus(record.status),
            question=record.question,
            plan=record.plan,
            research_notes=record.research_notes or [],
            draft=record.draft,
            critique=record.critique,
            final_answer=record.final_answer,
            iterations=record.iterations or 0,
            created_at=record.created_at,
        )

    @staticmethod
    async def stream_events(task_id: str) -> AsyncGenerator[AgentEvent, None]:
        queue = _event_queues.get(task_id)
        if not queue:
            return
        while True:
            event = await queue.get()
            if event is None:
                break
            yield event
        _event_queues.pop(task_id, None)


async def submit_feedback(task_id: str, feedback: str) -> bool:
    """Called from the feedback endpoint to resume the pipeline."""
    event = _task_feedback_events.get(task_id)
    if not event:
        return False
    _task_feedback[task_id] = feedback
    event.set()
    return True


async def _execute_pipeline(
    task_id: str,
    question: str,
    max_iterations: int,
    human_feedback: Optional[str],
) -> None:
    queue = _event_queues.get(task_id)
    orchestrator = get_orchestration_service()

    try:
        await _update_status(task_id, TaskStatus.RUNNING)

        # ── Phase 1: plan → research → write → critique ──
        phase1_state = {"question": question}

        async for event in orchestrator.run_streaming(
            question=question,
            max_iterations=max_iterations,
            phase1_only=True,
        ):
            if queue:
                await queue.put(event)

            if event.status == "awaiting_feedback" and event.agent == "pipeline":
                meta = event.metadata or {}
                phase1_state = {
                    "question": question,
                    "plan": meta.get("plan"),
                    "research_notes": meta.get("research_notes", []),
                    "search_results": [],
                    "draft": event.content,
                    "critique": meta.get("critique"),
                    "iteration": meta.get("iteration", 0),
                    "max_iterations": max_iterations,
                    "human_feedback": None,
                }

        # ── Pause: wait for human feedback ──
        _task_states[task_id] = phase1_state
        feedback_event = asyncio.Event()
        _task_feedback_events[task_id] = feedback_event

        logger.info("Task %s awaiting feedback", task_id)
        await feedback_event.wait()

        feedback_text = _task_feedback.pop(task_id, "")
        phase1_state["human_feedback"] = feedback_text or None
        logger.info("Task %s got feedback, running finalizer", task_id)

        # ── Phase 2: finalize ──
        if queue:
            await queue.put(AgentEvent(
                agent="finalizer", provider="OpenAI gpt-4o",
                status="started",
            ))

        final_answer = await orchestrator.run_finalizer(phase1_state)

        if queue:
            await queue.put(AgentEvent(
                agent="finalizer", provider="OpenAI gpt-4o",
                status="streaming", content=final_answer,
            ))
            await queue.put(AgentEvent(
                agent="finalizer", provider="OpenAI gpt-4o",
                status="completed",
            ))

        await _update_result(
            task_id=task_id,
            plan=phase1_state.get("plan"),
            research_notes=phase1_state.get("research_notes"),
            critique=phase1_state.get("critique"),
            final_answer=final_answer,
            iterations=phase1_state.get("iteration", 0),
        )

        if queue:
            await queue.put(AgentEvent(
                agent="pipeline", provider="system",
                status="completed", content=final_answer,
                metadata=phase1_state,
            ))

        await _update_status(task_id, TaskStatus.COMPLETED)

    except Exception as exc:
        logger.error("Task %s failed: %s", task_id, exc, exc_info=True)
        await _update_status(task_id, TaskStatus.FAILED, error=str(exc))
        if queue:
            await queue.put(AgentEvent(
                agent="pipeline", provider="system",
                status="error", content=str(exc),
            ))
    finally:
        _task_states.pop(task_id, None)
        _task_feedback_events.pop(task_id, None)
        _task_feedback.pop(task_id, None)
        if queue:
            await queue.put(None)


async def _update_status(
    task_id: str, status: TaskStatus, error: Optional[str] = None
) -> None:
    async with async_session_factory() as session:
        stmt = (
            update(TaskRecord)
            .where(TaskRecord.id == task_id)
            .values(status=status.value, error_message=error)
        )
        await session.execute(stmt)
        await session.commit()


async def _update_result(
    task_id: str,
    plan: Any = None,
    research_notes: Any = None,
    critique: Any = None,
    final_answer: Optional[str] = None,
    iterations: int = 0,
) -> None:
    async with async_session_factory() as session:
        stmt = (
            update(TaskRecord)
            .where(TaskRecord.id == task_id)
            .values(
                plan=plan,
                research_notes=research_notes,
                critique=critique,
                final_answer=final_answer,
                iterations=iterations,
            )
        )
        await session.execute(stmt)
        await session.commit()