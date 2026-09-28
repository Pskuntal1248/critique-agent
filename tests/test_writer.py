"""Tests for the writer node — mocks LLM, no real API calls."""

from unittest.mock import MagicMock, patch

from app.agents.nodes.writer import writer_node
from app.core.constants import AGENT_WRITER, STATUS_BEST_EFFORT, STATUS_COMPLETE

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_llm(report: str, tokens: int = 120) -> MagicMock:
    msg = MagicMock()
    msg.content = report
    msg.usage_metadata = {"total_tokens": tokens}
    llm = MagicMock()
    llm.invoke.return_value = msg
    return llm


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_writer_produces_final_report(base_state):
    base_state["analysis"] = "Key findings: fintech is growing."
    base_state["research_results"] = []
    report_text = "# Fintech Report\n\nExecutive summary...\n\n## Findings\n..."

    with patch("app.agents.nodes.writer.get_llm", return_value=_make_llm(report_text)):
        result = writer_node(base_state)

    assert result["final_report"] == report_text
    assert result["status"] == STATUS_COMPLETE
    assert result["active_agent"] == AGENT_WRITER
    assert result["errors"] == []


def test_writer_best_effort_when_max_revisions_hit(base_state):
    """When revision_count >= max_revisions, report gets a best-effort prefix."""
    from app.core.config import settings

    base_state["revision_count"] = settings.max_revisions
    base_state["analysis"] = "Reached max revisions."
    base_state["research_results"] = []

    with patch("app.agents.nodes.writer.get_llm", return_value=_make_llm("Final report.")):
        result = writer_node(base_state)

    assert result["status"] == STATUS_BEST_EFFORT
    assert "maximum revision limit" in result["final_report"]


def test_writer_includes_human_feedback_note(base_state):
    base_state["analysis"] = "analysis"
    base_state["research_results"] = []
    base_state["human_feedback"] = "Please emphasise risk section."

    captured_prompt = {}

    def fake_llm_factory(temperature=0.4):
        msg = MagicMock()
        msg.content = "Report with risk section"
        msg.usage_metadata = {"total_tokens": 90}
        llm = MagicMock()
        llm.invoke.side_effect = lambda msgs: (
            captured_prompt.update({"content": str(msgs[-1].content)}) or msg
        )
        return llm

    with patch("app.agents.nodes.writer.get_llm", side_effect=fake_llm_factory):
        result = writer_node(base_state)

    # The human note should have been embedded in the prompt
    assert "Please emphasise risk section" in captured_prompt["content"]
    assert result["final_report"] == "Report with risk section"


def test_writer_collects_sources_from_research_results(base_state):
    base_state["analysis"] = "analysis"
    base_state["research_results"] = [
        {
            "subtask": "sub1",
            "summary": "summary",
            "sources": [
                {"url": "https://source1.com", "title": "Source 1"},
                {"url": "https://source2.com", "title": "Source 2"},
            ],
        }
    ]
    captured_prompt = {}

    def fake_llm_factory(temperature=0.4):
        msg = MagicMock()
        msg.content = "Report"
        msg.usage_metadata = {}
        llm = MagicMock()
        llm.invoke.side_effect = lambda msgs: (
            captured_prompt.update({"content": str(msgs[-1].content)}) or msg
        )
        return llm

    with patch("app.agents.nodes.writer.get_llm", side_effect=fake_llm_factory):
        writer_node(base_state)

    assert "https://source1.com" in captured_prompt["content"]
    assert "https://source2.com" in captured_prompt["content"]


def test_writer_accumulates_tokens(base_state):
    base_state["analysis"] = "analysis"
    base_state["research_results"] = []
    base_state["tokens_used"] = 500

    with patch("app.agents.nodes.writer.get_llm", return_value=_make_llm("Report", tokens=100)):
        result = writer_node(base_state)

    assert result["tokens_used"] == 600


def test_writer_error_fallback(base_state):
    base_state["analysis"] = "analysis"
    base_state["research_results"] = []
    llm = MagicMock()
    llm.invoke.side_effect = RuntimeError("LLM unavailable")

    with patch("app.agents.nodes.writer.get_llm", return_value=llm):
        result = writer_node(base_state)

    assert result["final_report"] is None
    assert result["status"] == "failed"
    assert len(result["errors"]) == 1
    assert "writer" in result["errors"][0]
