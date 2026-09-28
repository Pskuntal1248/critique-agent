"""Researcher node — uses web_search and url_reader to gather data per subtask."""

import time

from langchain_core.messages import HumanMessage, SystemMessage
from tenacity import retry, stop_after_attempt, wait_exponential

from app.agents.state import AgentState
from app.agents.tools.url_reader import url_reader
from app.agents.tools.web_search import web_search
from app.core.constants import AGENT_RESEARCHER, STATUS_RESEARCHING, SYSTEM_RESEARCHER
from app.core.logging import get_logger
from app.services.llm.base import get_llm

logger = get_logger(__name__)

_RESEARCH_PROMPT = """\
You are researching the following subtask:
"{subtask}"

Context (overall task): "{task}"

Use the available tools to:
1. Search the web for relevant information (use web_search).
2. Read the 1-2 most relevant URLs in detail (use url_reader).

After gathering information, produce a concise research summary for this subtask.
Include the most important facts, numbers, and source URLs.
"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def _research_subtask(subtask: str, task: str) -> tuple[dict, int, int, int]:
    """Research a single subtask.

    Returns (result_dict, total_tokens, prompt_tokens, completion_tokens).
    """
    llm = get_llm(temperature=0.1)
    tools = [web_search, url_reader]
    llm_with_tools = llm.bind_tools(tools)

    messages = [
        SystemMessage(content=SYSTEM_RESEARCHER),
        HumanMessage(content=_RESEARCH_PROMPT.format(subtask=subtask, task=task)),
    ]

    # Agentic loop — keep calling until no more tool calls
    tool_map = {t.name: t for t in tools}
    sources: list[dict] = []
    total_tokens = prompt_tokens = completion_tokens = 0

    for _ in range(6):  # max 6 tool calls per subtask
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
            break  # LLM finished — no more tool calls

        from langchain_core.messages import ToolMessage  # noqa: PLC0415

        for tc in response.tool_calls:
            tool_fn = tool_map.get(tc["name"])
            if tool_fn is None:
                continue
            tool_result = tool_fn.invoke(tc["args"])
            messages.append(ToolMessage(content=str(tool_result), tool_call_id=tc["id"]))

            if tc["name"] == "web_search":
                if isinstance(tool_result, list):
                    sources.extend(tool_result[:3])
            elif tc["name"] == "url_reader":
                if isinstance(tool_result, dict) and not tool_result.get("error"):
                    sources.append(
                        {
                            "url": tool_result["url"],
                            "title": tool_result["title"],
                            "snippet": tool_result["text"][:300],
                        }
                    )

    summary = str(messages[-1].content) if messages else "No research data gathered."
    return (
        {"subtask": subtask, "summary": summary, "sources": sources[:10]},
        total_tokens,
        prompt_tokens,
        completion_tokens,
    )


def researcher_node(state: AgentState) -> dict:
    """LangGraph node: research all subtasks."""
    t0 = time.monotonic()
    logger.info("researcher_start", task_id=state["task_id"], subtasks=len(state["subtasks"]))

    results = []
    total_tokens = state.get("tokens_used", 0)
    total_prompt = state.get("prompt_tokens_used", 0)
    total_completion = state.get("completion_tokens_used", 0)
    errors = []

    for subtask in state["subtasks"]:
        try:
            result, tokens, prompt_tok, completion_tok = _research_subtask(
                subtask, state["original_task"]
            )
            results.append(result)
            total_tokens += tokens
            total_prompt += prompt_tok
            total_completion += completion_tok
        except Exception as exc:
            logger.warning("researcher_subtask_failed", subtask=subtask[:60], error=str(exc))
            errors.append(f"researcher [{subtask[:40]}]: {exc}")
            results.append({"subtask": subtask, "summary": "Research failed.", "sources": []})

    duration_ms = int((time.monotonic() - t0) * 1000)
    logger.info(
        "researcher_complete",
        task_id=state["task_id"],
        results=len(results),
        duration_ms=duration_ms,
    )
    return {
        "research_results": results,
        "status": STATUS_RESEARCHING,
        "active_agent": AGENT_RESEARCHER,
        "tokens_used": total_tokens,
        "prompt_tokens_used": total_prompt,
        "completion_tokens_used": total_completion,
        "errors": errors,
    }
