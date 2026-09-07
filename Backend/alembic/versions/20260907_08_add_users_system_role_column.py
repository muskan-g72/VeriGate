"""Add users.system_role column.

Revision ID: 20260907_08
Revises: 20260907_07
Create Date: 2026-09-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260907_08"
down_revision: str | Sequence[str] | None = "20260907_07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "system_role",
            sa.String(length=20),
            server_default=sa.text("'user'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "system_role")
