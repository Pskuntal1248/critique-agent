"""Writer node — generates the final polished report with source citations."""

import time

from langchain_core.messages import HumanMessage, SystemMessage
from tenacity import retry, stop_after_attempt, wait_exponential

from app.agents.state import AgentState
from app.core.constants import (
    AGENT_WRITER,
    STATUS_BEST_EFFORT,
    STATUS_COMPLETE,
    SYSTEM_WRITER,
)
from app.core.logging import get_logger
from app.services.llm.base import get_llm

logger = get_logger(__name__)

_WRITER_PROMPT = """\
Original task: {task}

Analysis:
{analysis}

Research sources used:
{sources}

{human_note}

Write the final report now.
"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def _call_llm(
    task: str, analysis: str, sources: str, human_note: str
) -> tuple[str, int, int, int]:
    """Returns (report_text, total_tokens, prompt_tokens, completion_tokens)."""
    llm = get_llm(temperature=0.4)
    messages = [
        SystemMessage(content=SYSTEM_WRITER),
        HumanMessage(
            content=_WRITER_PROMPT.format(
                task=task, analysis=analysis, sources=sources, human_note=human_note
            )
        ),
    ]
    response = llm.invoke(messages)
    content = str(response.content)

    usage = getattr(response, "usage_metadata", None) or {}
    if isinstance(usage, dict):
        prompt_tok = usage.get("input_tokens", 0)
        completion_tok = usage.get("output_tokens", 0)
        total_tok = usage.get("total_tokens", prompt_tok + completion_tok)
    else:
        prompt_tok = completion_tok = total_tok = 0

    return content, total_tok, prompt_tok, completion_tok


def _collect_sources(research_results: list[dict]) -> str:
    """Build markdown source list for the LLM prompt."""
    seen: set[str] = set()
    lines = []
    for r in research_results:
        for s in r.get("sources", []):
            url = s.get("url", "")
            if url and url not in seen:
                seen.add(url)
                lines.append(f"- [{s.get('title', url)}]({url})")
    return "\n".join(lines[:15]) if lines else "No external sources cited."


def _append_sources_section(report: str, research_results: list[dict]) -> str:
    """Append a deduplicated ## Sources section at the end of the report."""
    seen: set[str] = set()
    citations: list[str] = []
    for r in research_results:
        for s in r.get("sources", []):
            url = s.get("url", "")
            if url and url not in seen:
                seen.add(url)
                title = s.get("title") or url
                citations.append(f"{len(citations) + 1}. [{title}]({url})")
    if not citations:
        return report
    sources_block = "\n\n---\n\n## Sources\n\n" + "\n".join(citations[:20])
    return report + sources_block


def writer_node(state: AgentState) -> dict:
    """LangGraph node: write the final report."""
    t0 = time.monotonic()
    logger.info("writer_start", task_id=state["task_id"])

    from app.core.config import settings  # noqa: PLC0415

    best_effort = state.get("revision_count", 0) >= settings.max_revisions
    human_note = ""
    if state.get("human_feedback"):
        human_note = f"Note from human reviewer: {state['human_feedback']}"

    sources = _collect_sources(state.get("research_results", []))

    try:
        report, tokens, prompt_tok, completion_tok = _call_llm(
            state["original_task"],
            state.get("analysis", ""),
            sources,
            human_note,
        )

        # Deterministically append a ## Sources section from research data
        report = _append_sources_section(report, state.get("research_results", []))

        if best_effort:
            report = (
                "*Note: This report was produced after reaching the maximum revision limit.*\n\n"
                + report
            )

        duration_ms = int((time.monotonic() - t0) * 1000)
        logger.info(
            "writer_complete",
            task_id=state["task_id"],
            chars=len(report),
            best_effort=best_effort,
            duration_ms=duration_ms,
        )
        return {
            "final_report": report,
            "status": STATUS_BEST_EFFORT if best_effort else STATUS_COMPLETE,
            "active_agent": AGENT_WRITER,
            "tokens_used": state.get("tokens_used", 0) + tokens,
            "prompt_tokens_used": state.get("prompt_tokens_used", 0) + prompt_tok,
            "completion_tokens_used": state.get("completion_tokens_used", 0) + completion_tok,
            "errors": [],
        }
    except Exception as exc:
        logger.error("writer_failed", task_id=state["task_id"], error=str(exc))
        return {
            "final_report": None,
            "status": "failed",
            "active_agent": AGENT_WRITER,
            "errors": [f"writer: {exc}"],
        }
