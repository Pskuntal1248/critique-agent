"""Audit endpoints — replay historical events and steps for any task."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.task import (
    AgentEventResponse,
    AgentStepResponse,
    ReviewCriticNote,
    ReviewResponse,
    ReviewSource,
)
from app.core.auth import require_api_key
from app.models.agent_event import AgentEvent
from app.models.agent_step import AgentStep
from app.models.database import get_db
from app.models.task_run import TaskRun

router = APIRouter(prefix="/tasks", tags=["audit"])


async def _assert_task_exists(db: AsyncSession, task_id: str) -> None:
    """Raise 404 if the task_id doesn't exist in task_runs."""
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")
    run = await db.scalar(select(TaskRun).where(TaskRun.id == task_uuid))
    if run is None:
        raise HTTPException(status_code=404, detail="Task not found")


@router.get(
    "/{task_id}/events",
    response_model=list[AgentEventResponse],
    dependencies=[Depends(require_api_key)],
    summary="List all SSE events recorded for a task",
)
async def get_task_events(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[AgentEventResponse]:
    """Return every AgentEvent row for this task in chronological order.

    Useful for replaying the full execution after the stream has closed.
    """
    await _assert_task_exists(db, task_id)
    result = await db.execute(
        select(AgentEvent)
        .where(AgentEvent.task_id == uuid.UUID(task_id))
        .order_by(AgentEvent.id)
    )
    return [
        AgentEventResponse(
            id=ev.id,
            event_type=ev.event_type,
            agent_name=ev.agent_name,
            data=ev.data,
            created_at=ev.created_at,
        )
        for ev in result.scalars()
    ]


@router.get(
    "/{task_id}/steps",
    response_model=list[AgentStepResponse],
    dependencies=[Depends(require_api_key)],
    summary="List all agent execution steps for a task",
)
async def get_task_steps(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[AgentStepResponse]:
    """Return every AgentStep row for this task in execution order.

    Includes per-step token usage, duration, and error details.
    """
    await _assert_task_exists(db, task_id)
    result = await db.execute(
        select(AgentStep)
        .where(AgentStep.task_id == uuid.UUID(task_id))
        .order_by(AgentStep.step_number)
    )
    return [
        AgentStepResponse(
            id=step.id,
            agent_name=step.agent_name,
            step_number=step.step_number,
            status=step.status,
            output_summary=step.output_summary,
            tokens_used=step.tokens_used,
            duration_ms=step.duration_ms,
            error=step.error,
            created_at=step.created_at,
        )
        for step in result.scalars()
    ]


_MAX_ANALYSIS_CHARS = 100_000
_MAX_NOTE_CHARS = 4_000
_MAX_SOURCES = 30


@router.get(
    "/{task_id}/review",
    response_model=ReviewResponse,
    dependencies=[Depends(require_api_key)],
    summary="Full analysis draft, critic notes and sources for human review",
)
async def get_task_review(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> ReviewResponse:
    """Return the latest analysis draft plus critic feedback and researcher sources.

    Only an allow-list of fields is read from stored step output (analysis, critic
    score/feedback/approval, source title and http(s) url). Nothing else in
    output_data is exposed.
    """
    await _assert_task_exists(db, task_id)
    task_uuid = uuid.UUID(task_id)
    run = await db.scalar(select(TaskRun).where(TaskRun.id == task_uuid))
    steps = (
        await db.scalars(
            select(AgentStep)
            .where(AgentStep.task_id == task_uuid)
            .order_by(AgentStep.step_number)
        )
    ).all()

    analysis: str | None = None
    notes: list[ReviewCriticNote] = []
    sources: list[ReviewSource] = []
    seen: set[str] = set()

    for step in steps:
        data = step.output_data if isinstance(step.output_data, dict) else {}
        if step.agent_name == "analyst" and isinstance(data.get("analysis"), str):
            analysis = data["analysis"][:_MAX_ANALYSIS_CHARS]
        elif step.agent_name == "critic":
            score = data.get("critic_score")
            approved = data.get("critic_approved")
            notes.append(
                ReviewCriticNote(
                    round=len(notes) + 1,
                    score=float(score) if isinstance(score, (int, float)) else None,
                    approved=approved if isinstance(approved, bool) else None,
                    feedback=str(data.get("critic_feedback") or "")[:_MAX_NOTE_CHARS],
                )
            )
        elif step.agent_name == "researcher":
            for result in data.get("research_results") or []:
                if not isinstance(result, dict):
                    continue
                for src in result.get("sources") or []:
                    if not isinstance(src, dict):
                        continue
                    url = src.get("url")
                    if (
                        isinstance(url, str)
                        and url.startswith(("http://", "https://"))
                        and url not in seen
                        and len(sources) < _MAX_SOURCES
                    ):
                        seen.add(url)
                        title = src.get("title")
                        sources.append(
                            ReviewSource(
                                title=(title if isinstance(title, str) and title else url)[:300],
                                url=url[:1000],
                            )
                        )

    return ReviewResponse(
        task_id=task_id,
        status=run.status if run else "",
        revision_count=run.revision_count if run else 0,
        analysis=analysis,
        critic_notes=notes,
        sources=sources,
        human_feedback=run.human_feedback if run else None,
    )
