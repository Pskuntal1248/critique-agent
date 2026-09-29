from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.task import TaskCreateRequest, TaskResponse, TaskSummary
from app.core.auth import require_api_key
from app.models.database import get_db
from app.services.task_service import cancel_task, create_task, get_task, list_tasks

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _build_response(run) -> TaskResponse:
    """Build a TaskResponse from a TaskRun ORM object."""
    return TaskResponse(
        task_id=str(run.id),
        status=run.status,
        original_task=run.original_task,
        human_in_loop=run.human_in_loop,
        critic_score=run.critic_score,
        revision_count=run.revision_count,
        total_tokens=run.total_tokens,
        total_prompt_tokens=run.total_prompt_tokens,
        total_completion_tokens=run.total_completion_tokens,
        estimated_cost_usd=run.estimated_cost_usd,
        model_name=run.model_name,
        llm_provider=run.llm_provider,
        total_duration_ms=run.total_duration_ms,
        final_report=run.final_report,
        error=run.error,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


@router.post("", response_model=TaskResponse, dependencies=[Depends(require_api_key)])
async def create_task_endpoint(
    body: TaskCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Create a new task run and enqueue it for execution."""
    run = await create_task(db, body.task, human_in_loop=body.human_in_loop)
    return _build_response(run)


@router.get(
    "",
    response_model=list[TaskSummary],
    dependencies=[Depends(require_api_key)],
    summary="List recent tasks",
)
async def list_tasks_endpoint(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> list[TaskSummary]:
    """Return the most recent tasks, newest first (no report bodies)."""
    runs = await list_tasks(db, limit=limit)
    return [
        TaskSummary(
            task_id=str(r.id),
            status=r.status,
            original_task=r.original_task,
            human_in_loop=r.human_in_loop,
            critic_score=r.critic_score,
            revision_count=r.revision_count,
            total_tokens=r.total_tokens,
            estimated_cost_usd=r.estimated_cost_usd,
            total_duration_ms=r.total_duration_ms,
            created_at=r.created_at,
        )
        for r in runs
    ]


@router.get("/{task_id}", response_model=TaskResponse, dependencies=[Depends(require_api_key)])
async def get_task_endpoint(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """Get current status, cost metrics, and final report for a task."""
    run = await get_task(db, task_id)
    if not run:
        raise HTTPException(status_code=404, detail="Task not found")
    return _build_response(run)


@router.post(
    "/{task_id}/cancel",
    dependencies=[Depends(require_api_key)],
    summary="Cancel a running task",
)
async def cancel_task_endpoint(task_id: str) -> dict:
    """Cancel a queued or running task.

    Revokes the Celery job and marks the task as *cancelled*.
    Returns 404 if the task doesn't exist, 409 if it's already in a terminal
    state (complete / failed / cancelled).
    """
    # Validate UUID format first
    try:
        _ = __import__("uuid").UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")

    result = await cancel_task(task_id)
    if result == "not_found":
        raise HTTPException(status_code=404, detail="Task not found")
    if result == "already_terminal":
        raise HTTPException(
            status_code=409,
            detail="Task cannot be cancelled: already in a terminal state",
        )
    return {"task_id": task_id, "status": "cancelled"}
