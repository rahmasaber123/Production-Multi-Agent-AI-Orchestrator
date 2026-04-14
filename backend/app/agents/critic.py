

from __future__ import annotations

from typing import Any, Dict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.prompts import CRITIC_SYSTEM
from app.core.logging import get_logger
from app.models.schemas import Critique

logger = get_logger("agent.critic")

FALLBACK_CRITIQUE = {
    "issues": ["Critique unavailable"],
    "missing_points": [],
    "hallucination_risk": [],
    "score": 80,
    "fix_instructions": [],
}


async def critic_node(state: Dict[str, Any], llm: BaseChatModel) -> Dict[str, Any]:
    
    try:
        structured = llm.with_structured_output(Critique)
        critique_obj = await structured.ainvoke(
            [
                SystemMessage(content=CRITIC_SYSTEM),
                HumanMessage(
                    content=(
                        f"Question: {state['question']}\n\n"
                        f"Draft:\n{state['draft']}"
                    )
                ),
            ]
        )
        logger.info("Critique score: %d/100", critique_obj.score)
        return {
            "critique": critique_obj.model_dump(),
            "iteration": state["iteration"] + 1,
        }
    except Exception as exc:
        logger.error("Critic failed: %s — using fallback critique", exc)
        return {
            "critique": FALLBACK_CRITIQUE,
            "iteration": state["iteration"] + 1,
        }
