"""Pydantic models for agent structured outputs and API request/response schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════
# Agent structured output schemas (used by LLM .with_structured_output)
# ══════════════════════════════════════════════════════════════


class Plan(BaseModel):
    """Planner agent output: execution plan for the query."""
    steps: List[str] = Field(..., description="Ordered steps to answer the task.")
    key_risks: List[str] = Field(..., description="Major risks or unknowns to address.")
    desired_output_structure: List[str] = Field(
        ..., description="Section headings for final answer."
    )


class ResearchNotes(BaseModel):
    """Researcher agent output: categorized research findings."""
    cost_notes: List[str] = Field(..., description="Cost & pricing notes.")
    speed_notes: List[str] = Field(..., description="Speed & performance notes.")
    privacy_notes: List[str] = Field(..., description="Privacy & security notes.")
    reliability_notes: List[str] = Field(..., description="Reliability & uptime notes.")
    compliance_notes: List[str] = Field(..., description="Compliance & regulatory notes.")
    vendor_notes: List[str] = Field(..., description="Vendor lock-in risk notes.")
    summary_bullets: List[str] = Field(..., description="Top-level key takeaways.")


class Critique(BaseModel):
    """Critic agent output: structured quality assessment."""
    issues: List[str] = Field(..., description="Concrete problems with the draft.")
    missing_points: List[str] = Field(..., description="Important missing considerations.")
    hallucination_risk: List[str] = Field(
        ..., description="Claims needing source verification."
    )
    score: int = Field(..., ge=0, le=100, description="Quality score 0-100.")
    fix_instructions: List[str] = Field(
        ..., description="Actionable improvement steps."
    )


# ══════════════════════════════════════════════════════════════
# Graph state (used by LangGraph)
# ══════════════════════════════════════════════════════════════


class GraphState(BaseModel):
    """Complete state flowing through the LangGraph pipeline."""
    question: str
    plan: Optional[Dict[str, Any]] = None
    research_notes: List[str] = Field(default_factory=list)
    search_results: List[str] = Field(default_factory=list)
    draft: Optional[str] = None
    critique: Optional[Dict[str, Any]] = None
    human_feedback: Optional[str] = None
    iteration: int = 0
    max_iterations: int = 3


# ══════════════════════════════════════════════════════════════
# API request / response schemas
# ══════════════════════════════════════════════════════════════


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerateRequest(BaseModel):
    """POST /api/v1/generate body."""
    query: str = Field(
        ..., min_length=3, max_length=4000, description="User question or prompt."
    )
    max_iterations: int = Field(default=2, ge=1, le=5)
    human_feedback: Optional[str] = Field(
        default=None, max_length=2000, description="Optional human guidance."
    )


class AgentEvent(BaseModel):
    """Single event emitted during pipeline execution (SSE payload)."""
    agent: str
    provider: str
    status: str  # "started" | "streaming" | "completed" | "error"
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TaskResponse(BaseModel):
    """Final response returned to the client."""
    task_id: str
    status: TaskStatus
    question: str
    plan: Optional[Dict[str, Any]] = None
    research_notes: List[str] = Field(default_factory=list)
    draft: Optional[str] = None
    critique: Optional[Dict[str, Any]] = None
    final_answer: Optional[str] = None
    iterations: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class HealthResponse(BaseModel):
    status: str
    version: str
    providers: Dict[str, bool]
