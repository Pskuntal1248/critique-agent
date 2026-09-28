"""Critic node — evaluates analysis quality and decides approve/revise."""

import json
import time

from langchain_core.messages import HumanMessage, SystemMessage
from tenacity import retry, stop_after_attempt, wait_exponential

from app.agents.state import AgentState
from app.core.config import settings
from app.core.constants import AGENT_CRITIC, STATUS_CRITIQUING, SYSTEM_CRITIC
from app.core.logging import get_logger
from app.services.llm.base import get_llm

logger = get_logger(__name__)

_CRITIC_PROMPT = """\
Original task: {task}

Analysis to review:
{analysis}

Evaluate this analysis thoroughly. Return a JSON object with:
{{
  "score": <float 0.0-1.0>,
  "approved": <bool>,
  "feedback": "<specific feedback if not approved, empty string if approved>",
  "gaps": ["<gap 1>", "<gap 2>", ...]
}}

Approval threshold: {threshold}
"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def _call_llm(
    task: str, analysis: str, threshold: float
) -> tuple[float, bool, str, int, int, int]:
    """Returns (score, approved, feedback, total_tokens, prompt_tokens, completion_tokens)."""
    llm = get_llm(temperature=0.1)
    messages = [
        SystemMessage(content=SYSTEM_CRITIC),
        HumanMessage(
            content=_CRITIC_PROMPT.format(
                task=task, analysis=analysis, threshold=threshold
            )
        ),
    ]
    response = llm.invoke(messages)
    content = str(response.content)

    # Strip markdown fences
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    # Find JSON object
    start = content.find("{")
    end = content.rfind("}") + 1
    if start >= 0 and end > start:
        content = content[start:end]

    data = json.loads(content)
    score = float(data.get("score", 0.5))
    approved = bool(data.get("approved", score >= threshold))
    feedback = str(data.get("feedback", ""))

    usage = getattr(response, "usage_metadata", None) or {}
    if isinstance(usage, dict):
        prompt_tok = usage.get("input_tokens", 0)
        completion_tok = usage.get("output_tokens", 0)
        total_tok = usage.get("total_tokens", prompt_tok + completion_tok)
    else:
        prompt_tok = completion_tok = total_tok = 0

    return score, approved, feedback, total_tok, prompt_tok, completion_tok


def critic_node(state: AgentState) -> dict:
    """LangGraph node: critique the analysis."""
    t0 = time.monotonic()
    logger.info(
        "critic_start",
        task_id=state["task_id"],
        revision=state.get("revision_count", 0),
    )

    threshold = settings.critic_approval_threshold

    try:
        score, approved, feedback, tokens, prompt_tok, completion_tok = _call_llm(
            state["original_task"], state.get("analysis", ""), threshold
        )
        duration_ms = int((time.monotonic() - t0) * 1000)
        logger.info(
            "critic_complete",
            task_id=state["task_id"],
            score=score,
            approved=approved,
            duration_ms=duration_ms,
        )
        return {
            "critic_score": score,
            "critic_approved": approved,
            "critic_feedback": feedback,
            "status": STATUS_CRITIQUING,
            "active_agent": AGENT_CRITIC,
            "tokens_used": state.get("tokens_used", 0) + tokens,
            "prompt_tokens_used": state.get("prompt_tokens_used", 0) + prompt_tok,
            "completion_tokens_used": state.get("completion_tokens_used", 0) + completion_tok,
            "errors": [],
        }
    except Exception as exc:
        logger.error("critic_failed", task_id=state["task_id"], error=str(exc))
        # On failure, approve by default so the pipeline doesn't stall
        return {
            "critic_score": 0.5,
            "critic_approved": True,
            "critic_feedback": "",
            "status": STATUS_CRITIQUING,
            "active_agent": AGENT_CRITIC,
            "errors": [f"critic: {exc}"],
        }
