from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field


def _as_utc(value: datetime) -> datetime:
    """Aware values keep their offset. Naive values come from SQLite, which drops tzinfo.

    Every writer in this app stores datetime.now(UTC), so a naive stored value is UTC.
    """
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


UTCDateTime = Annotated[datetime, AfterValidator(_as_utc)]


class TaskCreateRequest(BaseModel):
    task: str = Field(
        ...,
        min_length=10,
        max_length=4000,
        description="Task description (10–4000 chars)",
    )
    human_in_loop: bool | None = Field(
        None, description="Override global HUMAN_IN_LOOP setting for this task"
    )


class TaskResponse(BaseModel):
    task_id: str
    status: str
    original_task: str
    human_in_loop: bool
    critic_score: float | None
    revision_count: int
    # Token & cost tracking
    total_tokens: int
    total_prompt_tokens: int
    total_completion_tokens: int
    estimated_cost_usd: float | None
    model_name: str | None
    llm_provider: str | None
    # Timing & output
    total_duration_ms: int | None
    final_report: str | None
    error: str | None
    created_at: UTCDateTime
    updated_at: UTCDateTime

    model_config = {"from_attributes": True}


class TaskSummary(BaseModel):
    """Lightweight task row for list views (no report body)."""

    task_id: str
    status: str
    original_task: str
    human_in_loop: bool
    critic_score: float | None
    revision_count: int
    total_tokens: int
    estimated_cost_usd: float | None
    total_duration_ms: int | None
    created_at: UTCDateTime


class HumanApproveRequest(BaseModel):
    decision: str = Field(
        ..., pattern="^(approve|reject|feedback)$",
        description="approve | reject | feedback"
    )
    feedback: str | None = Field(
        None,
        max_length=2000,
        description="Required when decision=feedback",
    )


# ─── Audit schemas ────────────────────────────────────────────────────────────

class AgentEventResponse(BaseModel):
    id: int
    event_type: str
    agent_name: str | None
    data: dict
    created_at: UTCDateTime

    model_config = {"from_attributes": True}


class AgentStepResponse(BaseModel):
    id: int
    agent_name: str
    step_number: int
    status: str
    output_summary: str | None
    tokens_used: int
    duration_ms: int | None
    error: str | None
    created_at: UTCDateTime

    model_config = {"from_attributes": True}


# ─── Export schema ────────────────────────────────────────────────────────────

class ReportExportResponse(BaseModel):
    task_id: str
    status: str
    original_task: str
    final_report: str
    critic_score: float | None
    revision_count: int
    total_tokens: int
    total_prompt_tokens: int
    total_completion_tokens: int
    estimated_cost_usd: float | None
    model_name: str | None
    llm_provider: str | None
    total_duration_ms: int | None
    created_at: UTCDateTime
    updated_at: UTCDateTime


# ─── Review schema ────────────────────────────────────────────────────────────

class ReviewSource(BaseModel):
    title: str
    url: str


class ReviewCriticNote(BaseModel):
    round: int
    score: float | None
    approved: bool | None
    feedback: str


class ReviewResponse(BaseModel):
    """What a human reviewer needs to judge the pending analysis.

    Built from a fixed allow-list of fields. Raw step output is never returned.
    """
    task_id: str
    status: str
    revision_count: int
    analysis: str | None
    critic_notes: list[ReviewCriticNote]
    sources: list[ReviewSource]
    human_feedback: str | None
