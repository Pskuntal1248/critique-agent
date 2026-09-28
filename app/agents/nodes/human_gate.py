"""Human gate node — pauses the graph for human approval using LangGraph interrupt."""

from langchain_core.messages import HumanMessage
from langgraph.types import interrupt

from app.agents.state import AgentState
from app.core.constants import (
    AGENT_HUMAN_GATE,
    HUMAN_APPROVE,
    STATUS_AWAITING_APPROVAL,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


def human_gate_node(state: AgentState) -> dict:
    """LangGraph node: pause execution and wait for human decision.

    Uses LangGraph's interrupt() to pause the graph. The graph resumes
    when Command(resume=decision_dict) is passed.

    decision_dict format:
        {"decision": "approve"}
        {"decision": "reject"}
        {"decision": "feedback", "feedback": "Please expand section 2..."}
    """
    logger.info(
        "human_gate_waiting",
        task_id=state["task_id"],
        critic_score=state.get("critic_score"),
    )

    # Pause the graph — this raises an interrupt that saves state via checkpointer
    decision: dict = interrupt(
        {
            "task_id": state["task_id"],
            "status": "awaiting_approval",
            "critic_score": state.get("critic_score"),
            "analysis_preview": (state.get("analysis", "") or "")[:500],
        }
    )

    human_decision = decision.get("decision", HUMAN_APPROVE)
    human_feedback = decision.get("feedback", "")

    logger.info(
        "human_gate_resumed",
        task_id=state["task_id"],
        decision=human_decision,
    )

    return {
        "human_decision": human_decision,
        "human_feedback": human_feedback if human_decision == "feedback" else None,
        "status": STATUS_AWAITING_APPROVAL,
        "active_agent": AGENT_HUMAN_GATE,
        "messages": [HumanMessage(content=f"Human decision: {human_decision}")],
    }
