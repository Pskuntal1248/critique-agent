"""Product readiness columns — cost tracking, model info, cancel support.

Adds to task_runs:
  total_prompt_tokens     — input/prompt token count
  total_completion_tokens — output/completion token count
  estimated_cost_usd      — estimated LLM spend in USD
  model_name              — e.g. claude-3-5-sonnet-20241022
  llm_provider            — anthropic | openai
  celery_task_id          — UUID of the Celery task (for cancellation)

Revision ID: 003
Revises: 002
Create Date: 2026-05-01 00:02:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("task_runs", sa.Column("total_prompt_tokens", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("task_runs", sa.Column("total_completion_tokens", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("task_runs", sa.Column("estimated_cost_usd", sa.Float(), nullable=True))
    op.add_column("task_runs", sa.Column("model_name", sa.String(length=50), nullable=True))
    op.add_column("task_runs", sa.Column("llm_provider", sa.String(length=20), nullable=True))
    op.add_column("task_runs", sa.Column("celery_task_id", sa.String(length=36), nullable=True))


def downgrade() -> None:
    op.drop_column("task_runs", "celery_task_id")
    op.drop_column("task_runs", "llm_provider")
    op.drop_column("task_runs", "model_name")
    op.drop_column("task_runs", "estimated_cost_usd")
    op.drop_column("task_runs", "total_completion_tokens")
    op.drop_column("task_runs", "total_prompt_tokens")
