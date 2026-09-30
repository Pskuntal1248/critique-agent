"""Human-in-the-loop endpoints — approve, reject, or give feedback on a paused task."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas.task import HumanApproveRequest
from app.core.auth import require_api_key
from app.services.task_service import approve_task

router = APIRouter(prefix="/tasks", tags=["human-in-the-loop"])


@router.post("/{task_id}/approve", dependencies=[Depends(require_api_key)])
async def approve_task_endpoint(
    task_id: str,
    body: HumanApproveRequest,
) -> dict:
    """Submit a human decision for a task awaiting approval.

    - **approve**: proceed to the Writer node and generate the final report.
    - **reject**: terminate the task as failed.
    - **feedback**: send feedback back to the Analyst for another revision cycle.
    """
    if body.decision == "feedback" and not body.feedback:
        raise HTTPException(
            status_code=422,
            detail="feedback text is required when decision=feedback",
        )

    resumed = await approve_task(task_id, body.decision, body.feedback)
    if not resumed:
        raise HTTPException(
            status_code=409,
            detail="Task is not currently awaiting human approval",
        )
    return {"task_id": task_id, "decision": body.decision, "status": "resumed"}
