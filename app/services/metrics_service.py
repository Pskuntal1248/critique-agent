"""Metrics service — aggregates run statistics from task_runs and agent_steps."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import STATUS_BEST_EFFORT, STATUS_COMPLETE
from app.models.agent_step import AgentStep
from app.models.task_run import TaskRun


async def get_metrics(db: AsyncSession, hours: int = 24) -> dict:
    """Return aggregated metrics for the last N hours."""
    since = datetime.now(UTC) - timedelta(hours=hours)

    # Total runs
    total_runs = await db.scalar(
        select(func.count()).where(TaskRun.created_at >= since)
    ) or 0

    # Success rate
    successful = await db.scalar(
        select(func.count()).where(
            TaskRun.created_at >= since,
            TaskRun.status.in_([STATUS_COMPLETE, STATUS_BEST_EFFORT]),
        )
    ) or 0

    # Average latency and tokens
    agg = await db.execute(
        select(
            func.avg(TaskRun.total_duration_ms),
            func.avg(TaskRun.total_tokens),
            func.percentile_cont(0.95).within_group(TaskRun.total_duration_ms),
        ).where(TaskRun.created_at >= since)
    )
    row = agg.one()
    avg_duration_ms = float(row[0] or 0)
    avg_tokens = float(row[1] or 0)
    p95_duration_ms = float(row[2] or 0)

    # Per-agent average duration
    agent_agg = await db.execute(
        select(AgentStep.agent_name, func.avg(AgentStep.duration_ms))
        .where(AgentStep.created_at >= since)
        .group_by(AgentStep.agent_name)
    )
    agent_latencies = {row[0]: round(float(row[1] or 0)) for row in agent_agg}

    # Average revisions per run
    avg_revisions = await db.scalar(
        select(func.avg(TaskRun.revision_count)).where(TaskRun.created_at >= since)
    ) or 0.0

    success_rate = round(successful / total_runs * 100, 1) if total_runs else 0.0

    return {
        "period_hours": hours,
        "runs_total": total_runs,
        "runs_successful": successful,
        "success_rate_pct": success_rate,
        "avg_duration_ms": round(avg_duration_ms),
        "p95_duration_ms": round(p95_duration_ms),
        "avg_tokens_per_run": round(avg_tokens),
        "avg_revisions": round(float(avg_revisions), 2),
        "agent_avg_latency_ms": agent_latencies,
    }
