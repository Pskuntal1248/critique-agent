"""Tests for the analyst node — mocks LLM, no real API calls."""

from unittest.mock import MagicMock, patch

from app.agents.nodes.analyst import _format_research, analyst_node
from app.core.constants import AGENT_ANALYST, STATUS_ANALYZING

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_llm(analysis: str = "Structured analysis.", tokens: int = 90) -> MagicMock:
    msg = MagicMock()
    msg.content = analysis
    msg.tool_calls = []
    msg.usage_metadata = {"total_tokens": tokens}

    llm = MagicMock()
    llm.bind_tools.return_value = llm
    llm.invoke.return_value = msg
    return llm


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_analyst_produces_analysis(base_state):
    base_state["research_results"] = [
        {"subtask": "Market size", "summary": "Market is $3B", "sources": []}
    ]
    with patch("app.agents.nodes.analyst.get_llm", return_value=_make_llm("Market analysis here")):
        result = analyst_node(base_state)

    assert result["analysis"] == "Market analysis here"
    assert result["status"] == STATUS_ANALYZING
    assert result["active_agent"] == AGENT_ANALYST
    assert result["errors"] == []


def test_analyst_includes_critic_feedback_in_prompt(base_state):
    base_state["research_results"] = []
    base_state["critic_feedback"] = "You missed the regulatory environment."
    base_state["revision_count"] = 1

    captured = {}

    def fake_llm_factory(temperature=0.3):
        msg = MagicMock()
        msg.content = "Revised analysis"
        msg.tool_calls = []
        msg.usage_metadata = {}

        llm = MagicMock()
        llm.bind_tools.return_value = llm
        llm.invoke.side_effect = lambda msgs: (
            captured.update({"prompt": str(msgs[-1].content)}) or msg
        )
        return llm

    with patch("app.agents.nodes.analyst.get_llm", side_effect=fake_llm_factory):
        result = analyst_node(base_state)

    assert "regulatory environment" in captured["prompt"]
    assert result["analysis"] == "Revised analysis"


def test_analyst_prefers_human_feedback_over_critic(base_state):
    base_state["research_results"] = []
    base_state["critic_feedback"] = "critic says X"
    base_state["human_feedback"] = "human says focus on revenue"
    base_state["revision_count"] = 1

    captured = {}

    def fake_llm_factory(temperature=0.3):
        msg = MagicMock()
        msg.content = "Human-guided analysis"
        msg.tool_calls = []
        msg.usage_metadata = {}

        llm = MagicMock()
        llm.bind_tools.return_value = llm
        llm.invoke.side_effect = lambda msgs: (
            captured.update({"prompt": str(msgs[-1].content)}) or msg
        )
        return llm

    with patch("app.agents.nodes.analyst.get_llm", side_effect=fake_llm_factory):
        analyst_node(base_state)

    # human_feedback takes precedence
    assert "focus on revenue" in captured["prompt"]


def test_analyst_accumulates_tokens(base_state):
    base_state["research_results"] = []
    base_state["tokens_used"] = 300
    with patch("app.agents.nodes.analyst.get_llm", return_value=_make_llm(tokens=75)):
        result = analyst_node(base_state)

    assert result["tokens_used"] == 375


def test_analyst_error_fallback(base_state):
    base_state["research_results"] = []
    llm = MagicMock()
    llm.bind_tools.return_value = llm
    llm.invoke.side_effect = RuntimeError("timeout")

    with patch("app.agents.nodes.analyst.get_llm", return_value=llm):
        result = analyst_node(base_state)

    assert "failed" in result["analysis"].lower()
    assert len(result["errors"]) == 1
    assert "analyst" in result["errors"][0]


# ── _format_research ──────────────────────────────────────────────────────────


def test_format_research_produces_markdown():
    results = [
        {
            "subtask": "Market size",
            "summary": "It's large.",
            "sources": [{"title": "Report", "url": "https://rpt.com"}],
        }
    ]
    text = _format_research(results)
    assert "Market size" in text
    assert "It's large." in text
    assert "https://rpt.com" in text


def test_format_research_empty():
    assert _format_research([]) == ""
