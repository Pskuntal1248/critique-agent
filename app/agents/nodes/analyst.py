"""Analyst node — synthesizes research into structured analysis."""

import time

from langchain_core.messages import HumanMessage, SystemMessage
from tenacity import retry, stop_after_attempt, wait_exponential

from app.agents.state import AgentState
from app.agents.tools.calculator import calculator
from app.agents.tools.file_reader import file_reader
from app.core.constants import AGENT_ANALYST, STATUS_ANALYZING, SYSTEM_ANALYST
from app.core.logging import get_logger
from app.services.llm.base import get_llm

logger = get_logger(__name__)

_ANALYST_PROMPT = """\
Original task: {task}

Research data collected:
{research_data}

{feedback_section}

Produce a structured analysis. Include:
1. Key findings per subtask
2. Patterns and trends
3. Gaps or uncertainties
4. Preliminary conclusions

Use the calculator tool for any numeric computations you need.
"""

_FEEDBACK_SECTION = """\
--- Previous critique feedback (revision {n}) ---
{feedback}

Please address every point in the feedback explicitly.
"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def _call_llm(
    task: str, research_data: str, feedback: str, revision: int
) -> tuple[str, int, int, int]:
    """Returns (analysis, total_tokens, prompt_tokens, completion_tokens)."""
    llm = get_llm(temperature=0.3)
    tools = [calculator, file_reader]
    llm_with_tools = llm.bind_tools(tools)

    feedback_section = (
        _FEEDBACK_SECTION.format(n=revision, feedback=feedback) if feedback else ""
    )
    messages = [
        SystemMessage(content=SYSTEM_ANALYST),
        HumanMessage(
            content=_ANALYST_PROMPT.format(
                task=task,
                research_data=research_data,
                feedback_section=feedback_section,
            )
        ),
    ]

    tool_map = {t.name: t for t in tools}
    total_tokens = prompt_tokens = completion_tokens = 0

    for _ in range(4):  # max tool calls
        response = llm_with_tools.invoke(messages)
        messages.append(response)
        usage = getattr(response, "usage_metadata", None) or {}
        if isinstance(usage, dict):
            p = usage.get("input_tokens", 0)
            c = usage.get("output_tokens", 0)
            prompt_tokens += p
            completion_tokens += c
            total_tokens += usage.get("total_tokens", p + c)

        if not getattr(response, "tool_calls", None):
            break

        from langchain_core.messages import ToolMessage  # noqa: PLC0415

        for tc in response.tool_calls:
            tool_fn = tool_map.get(tc["name"])
            if tool_fn:
                result = tool_fn.invoke(tc["args"])
                messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))

    analysis = str(messages[-1].content) if messages else "Analysis unavailable."
    return analysis, total_tokens, prompt_tokens, completion_tokens


def _format_research(research_results: list[dict]) -> str:
    parts = []
    for i, r in enumerate(research_results, 1):
        sources_str = "\n".join(
            f"  - [{s.get('title', 'Source')}]({s.get('url', '')})"
            for s in r.get("sources", [])[:3]
        )
        parts.append(
            f"### Subtask {i}: {r.get('subtask', '')}\n"
            f"{r.get('summary', '')}\n"
            f"Sources:\n{sources_str}"
        )
    return "\n\n".join(parts)


def analyst_node(state: AgentState) -> dict:
    """LangGraph node: analyze research data."""
    t0 = time.monotonic()
    logger.info(
        "analyst_start",
        task_id=state["task_id"],
        revision=state.get("revision_count", 0),
    )

    research_data = _format_research(state.get("research_results", []))

    # Use human feedback if available (after human gate rejection with feedback)
    feedback = state.get("human_feedback") or state.get("critic_feedback", "")
    revision = state.get("revision_count", 0)

    try:
        analysis, tokens, prompt_tok, completion_tok = _call_llm(
            state["original_task"], research_data, feedback, revision
        )
        duration_ms = int((time.monotonic() - t0) * 1000)
        logger.info(
            "analyst_complete",
            task_id=state["task_id"],
            chars=len(analysis),
            duration_ms=duration_ms,
        )
        return {
            "analysis": analysis,
            "status": STATUS_ANALYZING,
            "active_agent": AGENT_ANALYST,
            "tokens_used": state.get("tokens_used", 0) + tokens,
            "prompt_tokens_used": state.get("prompt_tokens_used", 0) + prompt_tok,
            "completion_tokens_used": state.get("completion_tokens_used", 0) + completion_tok,
            "errors": [],
        }
    except Exception as exc:
        logger.error("analyst_failed", task_id=state["task_id"], error=str(exc))
        return {
            "analysis": f"Analysis failed: {exc}",
            "status": STATUS_ANALYZING,
            "active_agent": AGENT_ANALYST,
            "errors": [f"analyst: {exc}"],
        }
