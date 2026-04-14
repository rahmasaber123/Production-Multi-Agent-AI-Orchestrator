"""SQLAlchemy ORM models for persistent storage."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskRecord(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    plan = Column(JSON, nullable=True)
    research_notes = Column(JSON, nullable=True)
    search_results = Column(JSON, nullable=True)
    draft = Column(Text, nullable=True)
    critique = Column(JSON, nullable=True)
    final_answer = Column(Text, nullable=True)
    human_feedback = Column(Text, nullable=True)
    iterations = Column(Integer, default=0)
    max_iterations = Column(Integer, default=2)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
