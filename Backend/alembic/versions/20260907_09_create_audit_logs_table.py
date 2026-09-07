"""Create audit_logs table.

Revision ID: 20260907_09
Revises: 20260907_08
Create Date: 2026-09-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260907_09"
down_revision: str | Sequence[str] | None = "20260907_08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("resource_type", sa.String(length=40), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column_name in (
        "user_id",
        "project_id",
        "action",
        "resource_type",
        "created_at",
    ):
        op.create_index(
            op.f(f"ix_audit_logs_{column_name}"),
            "audit_logs",
            [column_name],
            unique=False,
        )


def downgrade() -> None:
    for column_name in (
        "created_at",
        "resource_type",
        "action",
        "project_id",
        "user_id",
    ):
        op.drop_index(op.f(f"ix_audit_logs_{column_name}"), table_name="audit_logs")
    op.drop_table("audit_logs")
