import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TaskRun(Base):
    __tablename__ = "task_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    original_task: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")

    # Human-in-the-loop
    human_in_loop: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    human_decision: Mapped[str | None] = mapped_column(String(20), nullable=True)
    human_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Results
    final_report: Mapped[str | None] = mapped_column(Text, nullable=True)
    critic_score: Mapped[float | None] = mapped_column(nullable=True)
    revision_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Metrics
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_usd: Mapped[float | None] = mapped_column(nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    llm_provider: Mapped[str | None] = mapped_column(String(20), nullable=True)
    total_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Celery integration
    celery_task_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Error tracking
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
