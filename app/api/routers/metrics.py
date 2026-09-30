from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.metrics import MetricsResponse
from app.core.auth import require_api_key
from app.models.database import get_db
from app.services.metrics_service import get_metrics

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=MetricsResponse, dependencies=[Depends(require_api_key)])
async def metrics_endpoint(
    hours: int = Query(24, ge=1, le=168, description="Look-back window in hours (1–168)"),
    db: AsyncSession = Depends(get_db),
) -> MetricsResponse:
    """Return aggregated performance metrics."""
    data = await get_metrics(db, hours=hours)
    return MetricsResponse(**data)
