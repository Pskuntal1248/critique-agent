"""Planner node — decomposes the task into subtasks."""

import json
import time

from langchain_core.messages import HumanMessage, SystemMessage
from tenacity import retry, stop_after_attempt, wait_exponential

from app.agents.state import AgentState
from app.core.constants import AGENT_PLANNER, STATUS_PLANNING, SYSTEM_PLANNER
from app.core.logging import get_logger
from app.services.llm.base import get_llm

logger = get_logger(__name__)

_PLANNER_PROMPT = """\
Task: {task}

Decompose this task into 3-6 clear, researchable subtasks.

Respond with a JSON object exactly like this:
{{
  "subtasks": [
    "Subtask 1 description",
    "Subtask 2 description",
    ...
  ]
}}
"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def _call_llm(task: str) -> tuple[list[str], int, int, int]:
    """Call LLM and return (subtasks, total_tokens, prompt_tokens, completion_tokens)."""
    llm = get_llm(temperature=0.2)
    messages = [
        SystemMessage(content=SYSTEM_PLANNER),
        HumanMessage(content=_PLANNER_PROMPT.format(task=task)),
    ]
    response = llm.invoke(messages)
    content = str(response.content)

    # Parse JSON from response — handle optional markdown code blocks
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    data = json.loads(content)
    subtasks = data.get("subtasks", [])
    if not subtasks:
        raise ValueError("Planner returned empty subtasks list")

    usage = getattr(response, "usage_metadata", None) or {}
    if isinstance(usage, dict):
        prompt_tok = usage.get("input_tokens", 0)
        completion_tok = usage.get("output_tokens", 0)
        total_tok = usage.get("total_tokens", prompt_tok + completion_tok)
    else:
        prompt_tok = completion_tok = total_tok = 0

    return subtasks, total_tok, prompt_tok, completion_tok


def planner_node(state: AgentState) -> dict:
    """LangGraph node: plan the task."""
    t0 = time.monotonic()
    logger.info("planner_start", task_id=state["task_id"])

    try:
        subtasks, tokens, prompt_tok, completion_tok = _call_llm(state["original_task"])
        duration_ms = int((time.monotonic() - t0) * 1000)
        logger.info(
            "planner_complete",
            task_id=state["task_id"],
            subtasks=len(subtasks),
            tokens=tokens,
            duration_ms=duration_ms,
        )
        return {
            "subtasks": subtasks,
            "status": STATUS_PLANNING,
            "active_agent": AGENT_PLANNER,
            "tokens_used": state.get("tokens_used", 0) + tokens,
            "prompt_tokens_used": state.get("prompt_tokens_used", 0) + prompt_tok,
            "completion_tokens_used": state.get("completion_tokens_used", 0) + completion_tok,
            "errors": [],
        }
    except Exception as exc:
        logger.error("planner_failed", task_id=state["task_id"], error=str(exc))
        return {
            "subtasks": [state["original_task"]],  # fallback: treat task as single subtask
            "status": STATUS_PLANNING,
            "active_agent": AGENT_PLANNER,
            "errors": [f"planner: {exc}"],
        }
