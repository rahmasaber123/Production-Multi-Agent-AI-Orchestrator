

from __future__ import annotations

from typing import Any, Dict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.prompts import FINALIZER_SYSTEM
from app.core.logging import get_logger

logger = get_logger("agent.finalizer")


async def finalizer_node(
    state: Dict[str, Any], llm: BaseChatModel
) -> Dict[str, Any]:
    
    try:
        notes_text = "\n".join(state.get("research_notes", []))
        critique_txt = state.get("critique") or "No critique."
        feedback_txt = state.get("human_feedback") or "No human feedback."
        draft_txt = state.get("draft") or ""

        resp = await llm.ainvoke(
            [
                SystemMessage(content=FINALIZER_SYSTEM),
                HumanMessage(
                    content=(
                        f"Question: {state['question']}\n\n"
                        f"Plan: {state['plan']}\n\n"
                        f"Research notes:\n{notes_text}\n\n"
                        f"Critique: {critique_txt}\n\n"
                        f"Human feedback (HIGHEST PRIORITY): {feedback_txt}\n\n"
                        f"Current draft:\n{draft_txt}"
                    )
                ),
            ]
        )
        logger.info("Final answer produced: %d chars", len(resp.content))
        return {"draft": resp.content}
    except Exception as exc:
        logger.error("Finalizer failed: %s", exc)
        return {"draft": state.get("draft", f"[Finalization error: {exc}]")}
