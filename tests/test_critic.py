"""Tests for the critic node — mocks LLM, no real API calls."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.agents.nodes.critic import critic_node
from app.core.constants import AGENT_CRITIC, STATUS_CRITIQUING

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_llm(content: str, tokens: int = 60) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    msg.usage_metadata = {"total_tokens": tokens}
    llm = MagicMock()
    llm.invoke.return_value = msg
    return llm


def _critic_json(score: float, approved: bool, feedback: str = "") -> str:
    return json.dumps(
        {
            "score": score,
            "approved": approved,
            "feedback": feedback,
            "gaps": [],
        }
    )


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_critic_approves_high_score(base_state):
    base_state["analysis"] = "Very thorough analysis with data."
    payload = _critic_json(score=0.88, approved=True)
    with patch("app.agents.nodes.critic.get_llm", return_value=_make_llm(payload)):
        result = critic_node(base_state)

    assert result["critic_score"] == pytest.approx(0.88)
    assert result["critic_approved"] is True
    assert result["critic_feedback"] == ""
    assert result["status"] == STATUS_CRITIQUING
    assert result["active_agent"] == AGENT_CRITIC


def test_critic_rejects_low_score(base_state):
    base_state["analysis"] = "Thin analysis."
    payload = _critic_json(score=0.55, approved=False, feedback="Needs more data sources.")
    with patch("app.agents.nodes.critic.get_llm", return_value=_make_llm(payload)):
        result = critic_node(base_state)

    assert result["critic_score"] == pytest.approx(0.55)
    assert result["critic_approved"] is False
    assert "more data sources" in result["critic_feedback"]


def test_critic_strips_markdown_fences(base_state):
    base_state["analysis"] = "Some analysis."
    raw = f"Here is my evaluation:\n```json\n{_critic_json(0.9, True)}\n```"
    with patch("app.agents.nodes.critic.get_llm", return_value=_make_llm(raw)):
        result = critic_node(base_state)

    assert result["critic_score"] == pytest.approx(0.9)
    assert result["critic_approved"] is True


def test_critic_extracts_json_from_text_preamble(base_state):
    base_state["analysis"] = "analysis"
    payload = "Alright, here's my critique: " + _critic_json(0.8, True)
    with patch("app.agents.nodes.critic.get_llm", return_value=_make_llm(payload)):
        result = critic_node(base_state)

    assert result["critic_score"] == pytest.approx(0.8)
    assert result["critic_approved"] is True


def test_critic_accumulates_tokens(base_state):
    base_state["analysis"] = "ok"
    base_state["tokens_used"] = 100
    payload = _critic_json(0.8, True)
    with patch("app.agents.nodes.critic.get_llm", return_value=_make_llm(payload, tokens=40)):
        result = critic_node(base_state)

    assert result["tokens_used"] == 140


def test_critic_defaults_to_approved_on_llm_error(base_state):
    """On any failure, critic should approve by default so pipeline doesn't stall."""
    base_state["analysis"] = "some analysis"
    llm = MagicMock()
    llm.invoke.side_effect = RuntimeError("service unavailable")

    with patch("app.agents.nodes.critic.get_llm", return_value=llm):
        result = critic_node(base_state)

    assert result["critic_approved"] is True
    assert result["critic_score"] == pytest.approx(0.5)
    assert len(result["errors"]) == 1
    assert "critic" in result["errors"][0]
