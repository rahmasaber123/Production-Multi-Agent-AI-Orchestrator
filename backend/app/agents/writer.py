

from __future__ import annotations

from typing import Any, Dict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.prompts import WRITER_SYSTEM
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("agent.writer")


async def writer_node(state: Dict[str, Any], llm: BaseChatModel) -> Dict[str, Any]:
   
    try:
        notes_text = "\n".join(state.get("research_notes", []))
        search_text = "\n".join(state.get("search_results", [])[:2])
        critique_txt = state.get("critique") or "No critique yet — first draft."
        feedback_txt = state.get("human_feedback") or "No human feedback."

        resp = await llm.ainvoke(
            [
                SystemMessage(content=WRITER_SYSTEM),
                HumanMessage(
                    content=(
                        f"Question: {state['question']}\n\n"
                        f"Plan: {state['plan']}\n\n"
                        f"Research notes:\n{notes_text}\n\n"
                        f"Web context:\n{search_text}\n\n"
                        f"Critique: {critique_txt}\n\n"
                        f"Human feedback (highest priority): {feedback_txt}"
                    )
                ),
            ]
        )
        content = resp.content if hasattr(resp, "content") else str(resp)
        logger.info("Draft produced: %d chars", len(content))
        return {"draft": content}

    except Exception as exc:
        logger.warning("Writer primary LLM failed: %s — trying fallback", exc)
        try:
            settings = get_settings()
            fallback = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.4,
                api_key=settings.openai_api_key,
            )
            resp = await fallback.ainvoke(
                [
                    SystemMessage(content=WRITER_SYSTEM),
                    HumanMessage(
                        content=(
                            f"Question: {state['question']}\n"
                            f"Notes: {state.get('research_notes', [])}"
                        )
                    ),
                ]
            )
            return {"draft": resp.content}
        except Exception as exc2:
            logger.error("Writer fallback also failed: %s", exc2)
            return {"draft": f"[Writer error: {exc2}]"}
