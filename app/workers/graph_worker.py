"""Celery task — runs the full LangGraph pipeline for a single Critique task.

Design notes
------------
* Celery workers are *synchronous* processes.  asyncio.run() bridges into the
  async LangGraph/SQLAlchemy world.
* A fresh SQLAlchemy engine with NullPool is created per task so that event
  loops are never shared between Celery task invocations.
* Human-in-the-loop approval is handled by polling task_runs.human_decision
  in PostgreSQL every few seconds — no asyncio.Future, no in-process state.
* Each graph node emits an AgentEvent row.  The FastAPI SSE endpoint polls
  that table; no in-memory queues.
"""

import asyncio
import time
import uuid
from datetime import UTC, datetime

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.agents.graph import build_graph
from app.agents.state import AgentState
from app.core.config import settings
from app.core.constants import (
    ANTHROPIC_MODEL,
    EVENT_AGENT_COMPLETE,
    EVENT_AGENT_START,
    EVENT_AWAITING_APPROVAL,
    EVENT_TASK_COMPLETE,
    EVENT_TASK_FAILED,
    MODEL_PRICING,
    OPENAI_MODEL,
    STATUS_AWAITING_APPROVAL,
    STATUS_COMPLETE,
    STATUS_FAILED,
    STATUS_PENDING,
    STEP_COMPLETED,
)
from app.core.logging import get_logger
from app.models.agent_event import AgentEvent
from app.models.agent_step import AgentStep
from app.models.task_run import TaskRun
from app.workers.celery_app import celery_app

logger = get_logger(__name__)

_HUMAN_POLL_INTERVAL = 2.0   # seconds between DB polls when awaiting approval
_HUMAN_POLL_TIMEOUT = 3600.0  # 1 hour before auto-approve


# ─── Celery task entry point ──────────────────────────────────────────────────

@celery_app.task(bind=True, name="critique.run_graph")
def run_graph(self, task_id: str, original_task: str, human_in_loop: bool) -> None:  # type: ignore[type-arg]
    """Run the full LangGraph pipeline synchronously (via asyncio.run)."""
    logger.info("worker_task_started", task_id=task_id, celery_id=self.request.id)
    asyncio.run(_run_graph_async(task_id, original_task, human_in_loop))


# ─── Async implementation ─────────────────────────────────────────────────────

async def _run_graph_async(task_id: str, original_task: str, human_in_loop: bool) -> None:
    """Full pipeline coroutine — owns a dedicated DB engine for this invocation."""
    # NullPool: no connection reuse across asyncio.run() calls
    engine = create_async_engine(settings.database_url, poolclass=NullPool, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    t0 = time.monotonic()
    checkpointer = MemorySaver()
    graph = build_graph().compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": task_id}}

    initial_state: AgentState = {
        "task_id": task_id,
        "original_task": original_task,
        "subtasks": [],
        "research_results": [],
        "analysis": "",
        "critic_score": 0.0,
        "critic_feedback": "",
        "critic_approved": False,
        "revision_count": 0,
        "human_in_loop": human_in_loop,
        "human_decision": None,
        "human_feedback": None,
        "final_report": None,
        "status": STATUS_PENDING,
        "active_agent": "",
        "tokens_used": 0,
        "prompt_tokens_used": 0,
        "completion_tokens_used": 0,
        "errors": [],
        "messages": [],
    }

    step_number = 0

    try:
        input_or_command = initial_state
        while True:
            interrupt_value = None

            async for event in graph.astream(
                input_or_command, config=config, stream_mode="updates"
            ):
                for node_name, node_output in event.items():
                    if node_name == "__interrupt__":
                        interrupt_value = node_output
                        break

                    step_number += 1

                    # Emit agent_start before processing
                    await _emit_event(
                        session_factory, task_id, EVENT_AGENT_START, node_name,
                        {"agent": node_name, "step": step_number},
                    )

                    # Persist agent step record
                    await _persist_step(
                        session_factory,
                        task_id=task_id,
                        agent_name=node_name,
                        step_number=step_number,
                        status=STEP_COMPLETED,
                        output_data=_safe_dict(node_output),
                    )

                    # Update task_run status
                    await _update_task_status(
                        session_factory,
                        task_id=task_id,
                        status=node_output.get("status", ""),
                        tokens_used=node_output.get("tokens_used", 0),
                        critic_score=node_output.get("critic_score"),
                        revision_count=node_output.get("revision_count"),
                    )

                    # Emit agent_complete after node finished
                    await _emit_event(
                        session_factory, task_id, EVENT_AGENT_COMPLETE, node_name,
                        {
                            "agent": node_name,
                            "step": step_number,
                            "tokens": node_output.get("tokens_used", 0),
                            "status": node_output.get("status", ""),
                        },
                    )

                if interrupt_value is not None:
                    break  # exit astream loop

            if interrupt_value is not None:
                # Human approval required — update DB, publish event, then poll
                await _update_task_status(session_factory, task_id=task_id, status=STATUS_AWAITING_APPROVAL)

                interrupt_data = interrupt_value[0].value if interrupt_value else {}
                await _emit_event(
                    session_factory, task_id, EVENT_AWAITING_APPROVAL, None, interrupt_data
                )

                decision = await _poll_for_human_decision(session_factory, task_id)
                input_or_command = Command(resume=decision)
            else:
                break  # graph completed normally

        # ── Finalize ──────────────────────────────────────────────────────────
        final_state = graph.get_state(config)
        values = final_state.values if final_state else {}

        total_duration_ms = int((time.monotonic() - t0) * 1000)
        final_status = values.get("status", STATUS_COMPLETE)
        final_report = values.get("final_report")
        total_tokens = values.get("tokens_used", 0)
        prompt_tokens = values.get("prompt_tokens_used", 0)
        completion_tokens = values.get("completion_tokens_used", 0)

        # Cost estimation
        model_name = ANTHROPIC_MODEL if settings.llm_provider == "anthropic" else OPENAI_MODEL
        pricing = MODEL_PRICING.get(model_name, {"input": 3.0, "output": 15.0})
        estimated_cost = (
            prompt_tokens * pricing["input"] + completion_tokens * pricing["output"]
        ) / 1_000_000

        await _finalize_task(
            session_factory,
            task_id=task_id,
            status=final_status,
            final_report=final_report,
            total_tokens=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost_usd=estimated_cost,
            model_name=model_name,
            llm_provider=settings.llm_provider,
            total_duration_ms=total_duration_ms,
        )
        await _emit_event(
            session_factory, task_id, EVENT_TASK_COMPLETE, None,
            {
                "task_id": task_id,
                "status": final_status,
                "total_tokens": total_tokens,
                "estimated_cost_usd": round(estimated_cost, 6),
                "duration_ms": total_duration_ms,
                "is_final": True,
            },
        )

    except Exception as exc:
        logger.error("graph_execution_failed", task_id=task_id, error=str(exc))
        total_duration_ms = int((time.monotonic() - t0) * 1000)
        await _finalize_task(
            session_factory,
            task_id=task_id,
            status=STATUS_FAILED,
            error=str(exc),
            total_duration_ms=total_duration_ms,
        )
        await _emit_event(
            session_factory, task_id, EVENT_TASK_FAILED, None,
            {"task_id": task_id, "error": str(exc), "is_final": True},
        )

    finally:
        await engine.dispose()


# ─── Human-in-the-loop polling ────────────────────────────────────────────────

async def _poll_for_human_decision(
    session_factory: async_sessionmaker,
    task_id: str,
) -> dict:
    """Poll task_runs.human_decision until it's set, then return the decision dict."""
    task_uuid = uuid.UUID(task_id)
    deadline = time.monotonic() + _HUMAN_POLL_TIMEOUT

    while time.monotonic() < deadline:
        async with session_factory() as db:
            run = await db.scalar(select(TaskRun).where(TaskRun.id == task_uuid))
            if run and run.human_decision:
                result: dict = {"decision": run.human_decision}
                if run.human_feedback:
                    result["feedback"] = run.human_feedback
                logger.info(
                    "human_decision_received",
                    task_id=task_id,
                    decision=run.human_decision,
                )
                return result
        await asyncio.sleep(_HUMAN_POLL_INTERVAL)

    # Timeout — auto-approve so the pipeline doesn't hang forever
    logger.warning("human_gate_timeout", task_id=task_id)
    return {"decision": "approve"}


# ─── Persistence helpers ──────────────────────────────────────────────────────

async def _emit_event(
    session_factory: async_sessionmaker,
    task_id: str,
    event_type: str,
    agent_name: str | None,
    data: dict,
) -> None:
    """Write an AgentEvent row (SSE endpoint polls this table)."""
    try:
        async with session_factory() as db:
            db.add(
                AgentEvent(
                    task_id=uuid.UUID(task_id),
                    event_type=event_type,
                    agent_name=agent_name,
                    data={**data, "timestamp": datetime.now(UTC).isoformat()},
                )
            )
            await db.commit()
    except Exception as exc:
        logger.warning("emit_event_failed", task_id=task_id, event_type=event_type, error=str(exc))


async def _persist_step(
    session_factory: async_sessionmaker,
    task_id: str,
    agent_name: str,
    step_number: int,
    status: str,
    output_data: dict | None = None,
    error: str | None = None,
) -> None:
    try:
        async with session_factory() as db:
            db.add(
                AgentStep(
                    task_id=uuid.UUID(task_id),
                    agent_name=agent_name,
                    step_number=step_number,
                    status=status,
                    output_summary=(
                        str(output_data.get("status", ""))[:200] if output_data else None
                    ),
                    output_data=output_data,
                    tokens_used=output_data.get("tokens_used", 0) if output_data else 0,
                    error=error,
                )
            )
            await db.commit()
    except Exception as exc:
        logger.warning("persist_step_failed", task_id=task_id, error=str(exc))


async def _update_task_status(
    session_factory: async_sessionmaker,
    task_id: str,
    status: str,
    tokens_used: int = 0,
    critic_score: float | None = None,
    revision_count: int | None = None,
) -> None:
    if not status:
        return
    try:
        async with session_factory() as db:
            run = await db.scalar(
                select(TaskRun).where(TaskRun.id == uuid.UUID(task_id))
            )
            if run:
                run.status = status
                run.updated_at = datetime.now(UTC)
                if tokens_used:
                    run.total_tokens = tokens_used
                if critic_score is not None:
                    run.critic_score = critic_score
                if revision_count is not None:
                    run.revision_count = revision_count
                await db.commit()
    except Exception as exc:
        logger.warning("update_task_status_failed", task_id=task_id, error=str(exc))


async def _finalize_task(
    session_factory: async_sessionmaker,
    task_id: str,
    status: str,
    final_report: str | None = None,
    error: str | None = None,
    total_tokens: int = 0,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    estimated_cost_usd: float | None = None,
    model_name: str | None = None,
    llm_provider: str | None = None,
    total_duration_ms: int = 0,
) -> None:
    try:
        async with session_factory() as db:
            run = await db.scalar(
                select(TaskRun).where(TaskRun.id == uuid.UUID(task_id))
            )
            if run:
                run.status = status
                run.final_report = final_report
                run.error = error
                run.total_tokens = total_tokens
                run.total_prompt_tokens = prompt_tokens
                run.total_completion_tokens = completion_tokens
                run.estimated_cost_usd = estimated_cost_usd
                run.model_name = model_name
                run.llm_provider = llm_provider
                run.total_duration_ms = total_duration_ms
                run.updated_at = datetime.now(UTC)
                await db.commit()
    except Exception as exc:
        logger.warning("finalize_task_failed", task_id=task_id, error=str(exc))


# ─── Serialisation helper ─────────────────────────────────────────────────────

def _safe_dict(value: object) -> dict:
    """Convert node output to a JSON-serialisable dict."""
    if not isinstance(value, dict):
        return {}
    result = {}
    for k, v in value.items():
        if k == "messages":
            result[k] = [str(m) for m in (v or [])]
        elif isinstance(v, list) and v and hasattr(v[0], "__dict__"):
            result[k] = [str(i) for i in v]
        else:
            result[k] = v
    return result
