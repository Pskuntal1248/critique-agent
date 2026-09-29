from datetime import datetime

from pydantic import BaseModel, Field


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
    created_at: datetime
    updated_at: datetime

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
    created_at: datetime


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
    created_at: datetime

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
    created_at: datetime

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
    created_at: datetime
    updated_at: datetime
