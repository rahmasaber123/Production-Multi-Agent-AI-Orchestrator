

from __future__ import annotations

from typing import Any, Dict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.prompts import PLANNER_SYSTEM
from app.core.logging import get_logger
from app.models.schemas import Plan

logger = get_logger("agent.planner")

FALLBACK_PLAN = {
    "steps": ["Research topic", "Compare options", "Recommend"],
    "key_risks": ["Information may be outdated"],
    "desired_output_structure": [
        "Introduction",
        "Comparison",
        "Recommendation",
        "Risks",
    ],
}


async def planner_node(state: Dict[str, Any], llm: BaseChatModel) -> Dict[str, Any]:
    
    logger.info("Planning for: %s", state["question"][:80])
    try:
        structured = llm.with_structured_output(Plan)
        plan_obj = await structured.ainvoke(
            [
                SystemMessage(content=PLANNER_SYSTEM),
                HumanMessage(content=state["question"]),
            ]
        )
        logger.info("Plan created with %d steps", len(plan_obj.steps))
        return {"plan": plan_obj.model_dump()}
    except Exception as exc:
        logger.error("Planner failed: %s — using fallback plan", exc)
        return {"plan": FALLBACK_PLAN}
