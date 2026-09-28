"""Tests for the planner node — mocks LLM, no real API calls."""

import json
from unittest.mock import MagicMock, patch

from app.agents.nodes.planner import planner_node
from app.core.constants import AGENT_PLANNER, STATUS_PLANNING

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_llm(content: str, tokens: int = 80) -> MagicMock:
    """Return a mock LLM whose invoke() returns a fake AIMessage."""
    msg = MagicMock()
    msg.content = content
    msg.usage_metadata = {"total_tokens": tokens}

    llm = MagicMock()
    llm.invoke.return_value = msg
    return llm


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_planner_returns_subtasks(base_state):
    payload = json.dumps(
        {"subtasks": ["Understand fintech landscape", "Identify top players", "Assess gaps"]}
    )
    with patch("app.agents.nodes.planner.get_llm", return_value=_make_llm(payload)):
        result = planner_node(base_state)

    assert result["subtasks"] == [
        "Understand fintech landscape",
        "Identify top players",
        "Assess gaps",
    ]
    assert result["status"] == STATUS_PLANNING
    assert result["active_agent"] == AGENT_PLANNER
    assert result["tokens_used"] == 80


def test_planner_parses_markdown_code_block(base_state):
    """Planner should strip ```json fences before JSON parsing."""
    payload = '```json\n{"subtasks": ["Task A", "Task B", "Task C"]}\n```'
    with patch("app.agents.nodes.planner.get_llm", return_value=_make_llm(payload)):
        result = planner_node(base_state)

    assert len(result["subtasks"]) == 3
    assert result["subtasks"][0] == "Task A"


def test_planner_parses_plain_code_block(base_state):
    """Planner should also strip ``` (without json) fences."""
    payload = '```\n{"subtasks": ["Alpha", "Beta"]}\n```'
    with patch("app.agents.nodes.planner.get_llm", return_value=_make_llm(payload)):
        result = planner_node(base_state)

    assert len(result["subtasks"]) == 2


def test_planner_accumulates_tokens(base_state):
    """tokens_used should add to any existing token count in state."""
    base_state["tokens_used"] = 200
    payload = json.dumps({"subtasks": ["sub1", "sub2"]})
    with patch("app.agents.nodes.planner.get_llm", return_value=_make_llm(payload, tokens=50)):
        result = planner_node(base_state)

    assert result["tokens_used"] == 250


def test_planner_fallback_on_llm_error(base_state):
    """On LLM failure, planner falls back to treating the task as one subtask."""
    llm = MagicMock()
    llm.invoke.side_effect = Exception("API timeout")

    with patch("app.agents.nodes.planner.get_llm", return_value=llm):
        result = planner_node(base_state)

    # Should fall back gracefully — one subtask = the original task
    assert len(result["subtasks"]) == 1
    assert result["subtasks"][0] == base_state["original_task"]
    assert len(result["errors"]) == 1
    assert "planner" in result["errors"][0]


def test_planner_fallback_on_empty_subtasks(base_state):
    """If LLM returns empty subtasks list, planner should raise → fallback."""
    payload = json.dumps({"subtasks": []})
    with patch("app.agents.nodes.planner.get_llm", return_value=_make_llm(payload)):
        result = planner_node(base_state)

    # ValueError from _call_llm triggers the except branch
    assert len(result["subtasks"]) == 1
    assert result["subtasks"][0] == base_state["original_task"]
