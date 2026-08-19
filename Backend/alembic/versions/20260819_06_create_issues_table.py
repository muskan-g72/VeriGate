"""Create issues table.

Revision ID: 20260819_06
Revises: 20260819_05
Create Date: 2026-08-19
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260819_06"
down_revision: str | Sequence[str] | None = "20260819_05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "issues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("verification_result_id", sa.Uuid(), nullable=False),
        sa.Column("reported_by_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "severity",
            sa.String(length=20),
            server_default=sa.text("'medium'"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'open'"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["reported_by_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["verification_result_id"],
            ["verification_results.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column_name in (
        "project_id",
        "reported_by_id",
        "verification_result_id",
    ):
        op.create_index(
            op.f(f"ix_issues_{column_name}"),
            "issues",
            [column_name],
            unique=False,
        )


def downgrade() -> None:
    for column_name in (
        "verification_result_id",
        "reported_by_id",
        "project_id",
    ):
        op.drop_index(op.f(f"ix_issues_{column_name}"), table_name="issues")
    op.drop_table("issues")
