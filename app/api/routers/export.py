"""Export endpoints — download final reports as Markdown or JSON."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.task import ReportExportResponse
from app.core.auth import require_api_key
from app.models.database import get_db
from app.services.task_service import get_task

router = APIRouter(prefix="/tasks", tags=["export"])


@router.get(
    "/{task_id}/report.md",
    dependencies=[Depends(require_api_key)],
    summary="Download final report as Markdown",
    response_class=Response,
    responses={
        200: {"content": {"text/markdown": {}}, "description": "Markdown report"},
        404: {"description": "Task not found or report not yet available"},
    },
)
async def export_report_markdown(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Return the final report as a downloadable Markdown file."""
    try:
        _ = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")

    run = await get_task(db, task_id)
    if not run:
        raise HTTPException(status_code=404, detail="Task not found")
    if not run.final_report:
        raise HTTPException(status_code=404, detail="Report not yet available")

    short_id = task_id[:8]
    return Response(
        content=run.final_report,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="critique-{short_id}.md"'},
    )


@router.get(
    "/{task_id}/report.json",
    response_model=ReportExportResponse,
    dependencies=[Depends(require_api_key)],
    summary="Download final report as structured JSON",
)
async def export_report_json(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> ReportExportResponse:
    """Return the final report together with full task metadata as JSON."""
    try:
        _ = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")

    run = await get_task(db, task_id)
    if not run:
        raise HTTPException(status_code=404, detail="Task not found")
    if not run.final_report:
        raise HTTPException(status_code=404, detail="Report not yet available")

    return ReportExportResponse(
        task_id=str(run.id),
        status=run.status,
        original_task=run.original_task,
        final_report=run.final_report,
        critic_score=run.critic_score,
        revision_count=run.revision_count,
        total_tokens=run.total_tokens,
        total_prompt_tokens=run.total_prompt_tokens,
        total_completion_tokens=run.total_completion_tokens,
        estimated_cost_usd=run.estimated_cost_usd,
        model_name=run.model_name,
        llm_provider=run.llm_provider,
        total_duration_ms=run.total_duration_ms,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )
