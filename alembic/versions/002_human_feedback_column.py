"""Add human_feedback column to task_runs.

Revision ID: 002
Revises: 001
Create Date: 2026-05-01 00:01:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "task_runs",
        sa.Column("human_feedback", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("task_runs", "human_feedback")
