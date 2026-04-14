

from __future__ import annotations

from typing import Any, Dict, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.tools.tavily_search import TavilySearchResults

from app.agents.prompts import RESEARCHER_SYSTEM
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.schemas import ResearchNotes

logger = get_logger("agent.researcher")


def _build_search_tool() -> Optional[TavilySearchResults]:
    settings = get_settings()
    if settings.tavily_api_key:
        return TavilySearchResults(max_results=3, api_key=settings.tavily_api_key)
    logger.warning("TAVILY_API_KEY not set — web search disabled")
    return None


async def researcher_node(
    state: Dict[str, Any], llm: BaseChatModel
) -> Dict[str, Any]:
    
    search_results: list[str] = []
    search_tool = _build_search_tool()

    # ── Web search ───────────────────────────────────────────
    if search_tool:
        try:
            raw = await search_tool.ainvoke({"query": state["question"]})
            search_results = [
                r["content"]
                for r in raw
                if isinstance(r, dict) and "content" in r
            ]
            logger.info("Web search returned %d results", len(search_results))
        except Exception as exc:
            logger.warning("Web search failed: %s", exc)

    # ── Structured synthesis via LLM ─────────────────────────
    try:
        structured = llm.with_structured_output(ResearchNotes)
        search_ctx = "\n\n".join(search_results) if search_results else "No web results."
        notes_obj = await structured.ainvoke(
            [
                SystemMessage(content=RESEARCHER_SYSTEM),
                HumanMessage(
                    content=(
                        f"Question: {state['question']}\n\n"
                        f"Plan: {state['plan']}\n\n"
                        f"Web results:\n{search_ctx}"
                    )
                ),
            ]
        )
        all_notes = (
            [f"COST: {n}" for n in notes_obj.cost_notes]
            + [f"SPEED: {n}" for n in notes_obj.speed_notes]
            + [f"PRIVACY: {n}" for n in notes_obj.privacy_notes]
            + [f"RELIABILITY: {n}" for n in notes_obj.reliability_notes]
            + [f"COMPLIANCE: {n}" for n in notes_obj.compliance_notes]
            + [f"VENDOR: {n}" for n in notes_obj.vendor_notes]
            + [f"KEY: {n}" for n in notes_obj.summary_bullets]
        )
        logger.info("Research produced %d notes", len(all_notes))
        return {"research_notes": all_notes, "search_results": search_results}
    except Exception as exc:
        logger.error("Research synthesis failed: %s", exc)
        return {
            "research_notes": ["Research unavailable — proceeding with context only"],
            "search_results": search_results,
        }
