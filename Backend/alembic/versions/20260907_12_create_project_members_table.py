"""Create project_members table.

Revision ID: 20260907_12
Revises: 20260907_11
Create Date: 2026-09-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260907_12"
down_revision: str | Sequence[str] | None = "20260907_11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "project_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id",
            "user_id",
            name="uq_project_member_project_user",
        ),
    )
    for column_name in ("project_id", "user_id"):
        op.create_index(
            op.f(f"ix_project_members_{column_name}"),
            "project_members",
            [column_name],
            unique=False,
        )


def downgrade() -> None:
    for column_name in ("user_id", "project_id"):
        op.drop_index(
            op.f(f"ix_project_members_{column_name}"),
            table_name="project_members",
        )
    op.drop_table("project_members")
