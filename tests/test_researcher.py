"""Tests for the researcher node — mocks LLM and tools, no network."""

from unittest.mock import MagicMock, patch

from app.agents.nodes.researcher import researcher_node
from app.core.constants import AGENT_RESEARCHER, STATUS_RESEARCHING

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_no_tool_llm(summary: str = "Research complete.", tokens: int = 70) -> MagicMock:
    """LLM that immediately returns a summary without calling any tools."""
    msg = MagicMock()
    msg.content = summary
    msg.tool_calls = []
    msg.usage_metadata = {"total_tokens": tokens}

    llm = MagicMock()
    llm.bind_tools.return_value = llm
    llm.invoke.return_value = msg
    return llm


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_researcher_processes_single_subtask(base_state):
    base_state["subtasks"] = ["Identify fintech market size in Chile"]

    with patch("app.agents.nodes.researcher.get_llm", return_value=_make_no_tool_llm("Chile fintech = $2B")):
        result = researcher_node(base_state)

    assert len(result["research_results"]) == 1
    assert result["research_results"][0]["subtask"] == "Identify fintech market size in Chile"
    assert result["research_results"][0]["summary"] == "Chile fintech = $2B"
    assert result["status"] == STATUS_RESEARCHING
    assert result["active_agent"] == AGENT_RESEARCHER


def test_researcher_processes_multiple_subtasks(base_state):
    base_state["subtasks"] = ["sub1", "sub2", "sub3"]

    # _research_subtask now returns (result_dict, total_tokens, prompt_tokens, completion_tokens)
    def _mock_research(subtask, task):
        return ({"subtask": subtask, "summary": f"Result for {subtask}", "sources": []}, 50, 30, 20)

    with patch("app.agents.nodes.researcher._research_subtask", side_effect=_mock_research):
        result = researcher_node(base_state)

    assert len(result["research_results"]) == 3
    subtasks = [r["subtask"] for r in result["research_results"]]
    assert "sub1" in subtasks
    assert "sub2" in subtasks
    assert "sub3" in subtasks


def test_researcher_accumulates_tokens(base_state):
    base_state["subtasks"] = ["sub1", "sub2"]
    base_state["tokens_used"] = 100

    results_map = {
        "sub1": (50, 30, 20),
        "sub2": (60, 40, 20),
    }

    def _mock_research(subtask, task):
        total, prompt, completion = results_map[subtask]
        return ({"subtask": subtask, "summary": "ok", "sources": []}, total, prompt, completion)

    with patch("app.agents.nodes.researcher._research_subtask", side_effect=_mock_research):
        result = researcher_node(base_state)

    assert result["tokens_used"] == 210  # 100 + 50 + 60
    assert result["prompt_tokens_used"] == 70   # 30 + 40
    assert result["completion_tokens_used"] == 40  # 20 + 20


def test_researcher_continues_on_subtask_failure(base_state):
    """If one subtask fails, researcher should continue and log an error."""
    base_state["subtasks"] = ["failing sub", "working sub"]

    def _mock_research(subtask: str, task: str):
        if subtask == "failing sub":
            raise RuntimeError("network error")
        return ({"subtask": subtask, "summary": "Good result", "sources": []}, 60, 40, 20)

    # Patch _research_subtask directly (bypasses tenacity retry wrapper)
    with patch("app.agents.nodes.researcher._research_subtask", side_effect=_mock_research):
        result = researcher_node(base_state)

    # Both subtasks produce a result (failing one gets placeholder)
    assert len(result["research_results"]) == 2
    # Error is recorded
    assert len(result["errors"]) == 1
    assert "researcher" in result["errors"][0]
    # The failed subtask gets the fallback summary
    failed = next(r for r in result["research_results"] if r["subtask"] == "failing sub")
    assert "failed" in failed["summary"].lower()


def test_researcher_empty_subtasks(base_state):
    base_state["subtasks"] = []
    with patch("app.agents.nodes.researcher.get_llm", return_value=_make_no_tool_llm()):
        result = researcher_node(base_state)

    assert result["research_results"] == []
    assert result["errors"] == []
