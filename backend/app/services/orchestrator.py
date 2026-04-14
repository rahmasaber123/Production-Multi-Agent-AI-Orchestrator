"""LangGraph orchestration service — builds and executes the multi-agent pipeline."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional, TypedDict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.agents.llm_factory import make_llm, get_model_info
from app.agents.planner import planner_node
from app.agents.researcher import researcher_node
from app.agents.writer import writer_node
from app.agents.critic import critic_node
from app.agents.finalizer import finalizer_node
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import AgentEvent, GraphState

logger = get_logger("service.orchestrator")

# ── Provider labels for streaming events ─────────────────────
NODE_PROVIDERS = {
    "planner": "OpenAI gpt-4o-mini",
    "researcher": "Groq Llama-3.3-70B",
    "writer": "Ollama / fallback",
    "critic": "Groq Llama-3.3-70B",
    "finalizer": "OpenAI gpt-4o",
}


class _GraphState(TypedDict, total=False):
    question: str
    plan: Optional[Dict[str, Any]]
    research_notes: List[str]
    search_results: List[str]
    draft: Optional[str]
    critique: Optional[Dict[str, Any]]
    human_feedback: Optional[str]
    iteration: int
    max_iterations: int


class OrchestrationService:
    """Manages the multi-agent LangGraph pipeline lifecycle."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._llms = self._init_llms()
        self._graph = self._build_graph()
        self._graph_with_memory = self._build_graph(use_memory=True)
        self._graph_phase1 = self._build_graph(phase1_only=True)
        logger.info("OrchestrationService initialized")

    # ══════════════════════════════════════════════════════════
    # LLM initialization
    # ══════════════════════════════════════════════════════════

    def _init_llms(self) -> Dict[str, Any]:
        """Create LLM instances for each agent role."""
        settings = self._settings
        llms = {
            "planner": make_llm("openai", "gpt-4o-mini", temperature=0.0),
            "researcher": make_llm("groq", "llama-3.3-70b-versatile", temperature=0.1),
            "writer": make_llm(
                "ollama" if settings.use_ollama else "openai",
                settings.ollama_model if settings.use_ollama else "gpt-4o-mini",
                temperature=0.4,
            ),
            "critic": make_llm("groq", "llama-3.3-70b-versatile", temperature=0.0),
            "finalizer": make_llm("openai", "gpt-4o", temperature=0.3),
        }
        for role, llm in llms.items():
            logger.info("  %s → %s", role, get_model_info(llm))
        return llms

    # ══════════════════════════════════════════════════════════
    # Graph construction
    # ══════════════════════════════════════════════════════════

    def _should_revise(self, state: Dict[str, Any]) -> Literal["revise", "finalize"]:
        """Conditional edge: revise if score < 80 and iterations remain."""
        critique = state.get("critique")
        if critique is None:
            return "finalize"
        score = critique.get("score", 80)
        if state["iteration"] >= state["max_iterations"]:
            return "finalize"
        if score < 80:
            return "revise"
        return "finalize"

    def _build_graph(self, use_memory: bool = False, phase1_only: bool = False):
        """Construct and compile the LangGraph state graph."""
        llms = self._llms

        # Wrap agent nodes to inject their LLM dependency
        async def _planner(state):
            return await planner_node(state, llms["planner"])

        async def _researcher(state):
            return await researcher_node(state, llms["researcher"])

        async def _writer(state):
            return await writer_node(state, llms["writer"])

        async def _critic(state):
            return await critic_node(state, llms["critic"])

        async def _finalizer(state):
            return await finalizer_node(state, llms["finalizer"])

        workflow = StateGraph(_GraphState)
        workflow.add_node("planner", _planner)
        workflow.add_node("researcher", _researcher)
        workflow.add_node("writer", _writer)
        workflow.add_node("critic", _critic)

        if not phase1_only:
            workflow.add_node("finalizer", _finalizer)

        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "researcher")
        workflow.add_edge("researcher", "writer")
        workflow.add_edge("writer", "critic")
        workflow.add_conditional_edges(
            "critic",
            self._should_revise,
            {"revise": "writer", "finalize": END if phase1_only else "finalizer"},
        )

        if not phase1_only:
            workflow.add_edge("finalizer", END)

        if use_memory:
            return workflow.compile(checkpointer=MemorySaver())
        return workflow.compile()

    # ══════════════════════════════════════════════════════════
    # Execution: blocking (returns final result)
    # ══════════════════════════════════════════════════════════

    async def run(
        self,
        question: str,
        max_iterations: int = 2,
        human_feedback: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute the full pipeline and return the final state."""
        initial_state = {
            "question": question,
            "plan": None,
            "research_notes": [],
            "search_results": [],
            "draft": None,
            "critique": None,
            "human_feedback": human_feedback,
            "iteration": 0,
            "max_iterations": max_iterations,
        }
        logger.info("Starting pipeline for: %s", question[:80])
        result = await self._graph.ainvoke(initial_state)
        logger.info("Pipeline complete — iteration %d", result.get("iteration", 0))
        return result

    # ══════════════════════════════════════════════════════════
    # Execution: streaming (yields events via SSE)
    # ══════════════════════════════════════════════════════════

    async def run_streaming(
        self,
        question: str,
        max_iterations: int = 2,
        human_feedback: Optional[str] = None,
        phase1_only: bool = False,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Execute pipeline and yield AgentEvent objects for SSE streaming."""
        initial_state = {
            "question": question,
            "plan": None,
            "research_notes": [],
            "search_results": [],
            "draft": None,
            "critique": None,
            "human_feedback": human_feedback,
            "iteration": 0,
            "max_iterations": max_iterations,
        }

        graph = self._graph_phase1 if phase1_only else self._graph
        logger.info("Starting streaming pipeline for: %s", question[:80])
        final_state: Dict[str, Any] = {}

        async for event in graph.astream_events(initial_state, version="v2"):
            kind = event["event"]
            name = event.get("name", "")

            if kind == "on_chain_start" and name in NODE_PROVIDERS:
                yield AgentEvent(
                    agent=name,
                    provider=NODE_PROVIDERS[name],
                    status="started",
                )

            elif kind == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    # Determine which agent is currently streaming
                    parent_ids = event.get("parent_ids", [])
                    agent_name = event.get("metadata", {}).get("langgraph_node", "unknown")
                    yield AgentEvent(
                        agent=agent_name,
                        provider=NODE_PROVIDERS.get(agent_name, "unknown"),
                        status="streaming",
                        content=chunk.content,
                    )

            elif kind == "on_chain_end" and name in NODE_PROVIDERS:
                output = event.get("data", {}).get("output", {})
                metadata = {}
                if name == "planner" and isinstance(output, dict):
                    metadata["plan"] = output.get("plan")
                elif name == "researcher" and isinstance(output, dict):
                    metadata["research_notes"] = output.get("research_notes", [])
                elif name == "critic" and isinstance(output, dict):
                    metadata["critique"] = output.get("critique")
                    metadata["iteration"] = output.get("iteration")

                yield AgentEvent(
                    agent=name,
                    provider=NODE_PROVIDERS[name],
                    status="completed",
                    metadata=metadata if metadata else None,
                )
                # Track the latest state
                if isinstance(output, dict):
                    final_state.update(output)

        # Emit final done event
       # Emit final event
        if phase1_only:
            yield AgentEvent(
                agent="pipeline",
                provider="system",
                status="awaiting_feedback",
                content=final_state.get("draft"),
                metadata={
                    "plan": final_state.get("plan"),
                    "research_notes": final_state.get("research_notes", []),
                    "critique": final_state.get("critique"),
                    "iteration": final_state.get("iteration", 0),
                },
            )
        else:
            yield AgentEvent(
                agent="pipeline",
                provider="system",
                status="completed",
                content=final_state.get("draft"),
                metadata={
                    "plan": final_state.get("plan"),
                    "research_notes": final_state.get("research_notes", []),
                    "critique": final_state.get("critique"),
                    "iteration": final_state.get("iteration", 0),
                },
            )

    # ══════════════════════════════════════════════════════════
    # Health check
    # ══════════════════════════════════════════════════════════

    def get_provider_status(self) -> Dict[str, bool]:
        """Check which providers are configured."""
        s = self._settings
        return {
            "openai": bool(s.openai_api_key),
            "groq": bool(s.groq_api_key),
            "tavily": bool(s.tavily_api_key),
            "ollama": s.use_ollama,
            "langsmith": bool(s.langsmith_api_key),
        }
    async def run_finalizer(self, state: Dict[str, Any]) -> str:
        """Run the finalizer agent directly on a given state."""
        result = await finalizer_node(state, self._llms["finalizer"])
        return result.get("draft", "")

# ── Singleton ────────────────────────────────────────────────
_service: Optional[OrchestrationService] = None


def get_orchestration_service() -> OrchestrationService:
    global _service
    if _service is None:
        _service = OrchestrationService()
    return _service
