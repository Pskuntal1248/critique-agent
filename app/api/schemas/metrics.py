from pydantic import BaseModel


class MetricsResponse(BaseModel):
    period_hours: int
    runs_total: int
    runs_successful: int
    success_rate_pct: float
    avg_duration_ms: int
    p95_duration_ms: int
    avg_tokens_per_run: int
    avg_revisions: float
    agent_avg_latency_ms: dict[str, int]
