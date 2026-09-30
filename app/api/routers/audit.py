"""Audit endpoints — replay historical events and steps for any task."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.task import AgentEventResponse, AgentStepResponse
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
