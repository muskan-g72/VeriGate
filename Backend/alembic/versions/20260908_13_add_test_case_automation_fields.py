"""Add test case automation fields.

Revision ID: 20260908_13
Revises: 20260907_12
Create Date: 2026-09-08
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260908_13"
down_revision: str | Sequence[str] | None = "20260907_12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "test_cases",
        sa.Column(
            "execution_mode",
            sa.String(length=20),
            server_default=sa.text("'manual'"),
            nullable=False,
        ),
    )
    op.add_column(
        "test_cases",
        sa.Column(
            "automation_steps",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("test_cases", "automation_steps")
    op.drop_column("test_cases", "execution_mode")
