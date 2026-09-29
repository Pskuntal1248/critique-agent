"""Tests for graph routing functions — pure logic, no LLM or DB."""

from langgraph.graph import END

from app.agents.graph import increment_revision, route_after_critic, route_after_human_gate
from app.core.constants import (
    AGENT_ANALYST,
    AGENT_HUMAN_GATE,
    AGENT_WRITER,
    HUMAN_APPROVE,
    HUMAN_REJECT,
)

# ── route_after_critic ────────────────────────────────────────────────────────


def test_route_critic_not_approved_goes_to_analyst(base_state):
    base_state["critic_approved"] = False
    base_state["revision_count"] = 0
    assert route_after_critic(base_state) == AGENT_ANALYST


def test_route_critic_not_approved_multiple_revisions(base_state):
    base_state["critic_approved"] = False
    base_state["revision_count"] = 1
    assert route_after_critic(base_state) == AGENT_ANALYST


def test_route_critic_not_approved_at_max_revisions_goes_to_writer(base_state):
    from app.core.config import settings

    base_state["critic_approved"] = False
    base_state["revision_count"] = settings.max_revisions  # = 3
    base_state["human_in_loop"] = False
    # Max revisions hit → writer regardless of approval
    assert route_after_critic(base_state) == AGENT_WRITER


def test_route_critic_approved_no_hil_goes_to_writer(base_state):
    base_state["critic_approved"] = True
    base_state["human_in_loop"] = False
    assert route_after_critic(base_state) == AGENT_WRITER


def test_route_critic_approved_with_hil_goes_to_human_gate(base_state):
    base_state["critic_approved"] = True
    base_state["human_in_loop"] = True
    assert route_after_critic(base_state) == AGENT_HUMAN_GATE


def test_route_critic_max_revisions_with_hil_goes_to_human_gate(base_state):
    """Even at max revisions, if human_in_loop is True → go to human gate."""
    from app.core.config import settings

    base_state["critic_approved"] = False
    base_state["revision_count"] = settings.max_revisions
    base_state["human_in_loop"] = True
    assert route_after_critic(base_state) == AGENT_HUMAN_GATE


# ── route_after_human_gate ────────────────────────────────────────────────────


def test_route_human_gate_approve_goes_to_writer(base_state):
    base_state["human_decision"] = HUMAN_APPROVE
    assert route_after_human_gate(base_state) == AGENT_WRITER


def test_route_human_gate_reject_goes_to_end(base_state):
    base_state["human_decision"] = HUMAN_REJECT
    assert route_after_human_gate(base_state) == END


def test_route_human_gate_feedback_goes_to_analyst(base_state):
    base_state["human_decision"] = "feedback"
    assert route_after_human_gate(base_state) == AGENT_ANALYST


def test_route_human_gate_default_approve_when_no_decision(base_state):
    base_state["human_decision"] = None
    # Default is HUMAN_APPROVE → writer
    assert route_after_human_gate(base_state) == AGENT_WRITER


# ── increment_revision ────────────────────────────────────────────────────────


def test_increment_revision_from_zero(base_state):
    base_state["revision_count"] = 0
    result = increment_revision(base_state)
    assert result["revision_count"] == 1


def test_increment_revision_accumulates(base_state):
    base_state["revision_count"] = 2
    result = increment_revision(base_state)
    assert result["revision_count"] == 3


def test_increment_revision_only_returns_count_key(base_state):
    base_state["revision_count"] = 0
    result = increment_revision(base_state)
    # Should only update revision_count, nothing else
    assert set(result.keys()) == {"revision_count"}
