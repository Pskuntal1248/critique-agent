"""LangGraph StateGraph definition for Critique."""

from langgraph.graph import END, START, StateGraph

from app.agents.nodes.analyst import analyst_node
from app.agents.nodes.critic import critic_node
from app.agents.nodes.human_gate import human_gate_node
from app.agents.nodes.planner import planner_node
from app.agents.nodes.researcher import researcher_node
from app.agents.nodes.writer import writer_node
from app.agents.state import AgentState
from app.core.config import settings
from app.core.constants import (
    AGENT_ANALYST,
    AGENT_CRITIC,
    AGENT_HUMAN_GATE,
    AGENT_PLANNER,
    AGENT_RESEARCHER,
    AGENT_WRITER,
    HUMAN_APPROVE,
    HUMAN_REJECT,
)

# ─── Conditional edge functions ──────────────────────────────────────────────

def route_after_critic(state: AgentState) -> str:
    """Decide next node after critic evaluation."""
    approved = state.get("critic_approved", False)
    revision_count = state.get("revision_count", 0)

    if not approved and revision_count < settings.max_revisions:
        # Increment revision count and send back to analyst
        return AGENT_ANALYST

    # Approved (or max revisions hit) — go to human gate or writer
    if state.get("human_in_loop", False):
        return AGENT_HUMAN_GATE
    return AGENT_WRITER


def route_after_human_gate(state: AgentState) -> str:
    """Decide next node after human review."""
    decision = state.get("human_decision", HUMAN_APPROVE)
    if decision == HUMAN_REJECT:
        return END  # type: ignore[return-value]
    if decision == "feedback":
        return AGENT_ANALYST  # re-analyze with human feedback
    return AGENT_WRITER  # approve → write


def increment_revision(state: AgentState) -> dict:
    """Increment revision counter before sending back to analyst."""
    return {"revision_count": state.get("revision_count", 0) + 1}


# ─── Graph builder ────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Build and return the compiled Critique graph."""
    builder = StateGraph(AgentState)

    # Add all nodes
    builder.add_node(AGENT_PLANNER, planner_node)
    builder.add_node(AGENT_RESEARCHER, researcher_node)
    builder.add_node(AGENT_ANALYST, analyst_node)
    builder.add_node(AGENT_CRITIC, critic_node)
    builder.add_node(AGENT_HUMAN_GATE, human_gate_node)
    builder.add_node(AGENT_WRITER, writer_node)
    builder.add_node("increment_revision", increment_revision)

    # Entry point
    builder.add_edge(START, AGENT_PLANNER)

    # Linear edges
    builder.add_edge(AGENT_PLANNER, AGENT_RESEARCHER)
    builder.add_edge(AGENT_RESEARCHER, AGENT_ANALYST)
    builder.add_edge(AGENT_ANALYST, AGENT_CRITIC)

    # Critic → conditional branch
    builder.add_conditional_edges(
        AGENT_CRITIC,
        route_after_critic,
        {
            AGENT_ANALYST: "increment_revision",  # needs revision → bump counter first
            AGENT_HUMAN_GATE: AGENT_HUMAN_GATE,
            AGENT_WRITER: AGENT_WRITER,
        },
    )
    builder.add_edge("increment_revision", AGENT_ANALYST)

    # Human gate → conditional branch
    builder.add_conditional_edges(
        AGENT_HUMAN_GATE,
        route_after_human_gate,
        {
            AGENT_ANALYST: AGENT_ANALYST,
            AGENT_WRITER: AGENT_WRITER,
            END: END,
        },
    )

    # Writer always ends
    builder.add_edge(AGENT_WRITER, END)

    return builder
