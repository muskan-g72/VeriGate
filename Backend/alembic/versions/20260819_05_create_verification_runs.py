"""Create verification runs and results.

Revision ID: 20260819_05
Revises: 20260819_04
Create Date: 2026-08-19
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260819_05"
down_revision: str | Sequence[str] | None = "20260819_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "verification_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("test_suite_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["test_suite_id"], ["test_suites.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_verification_runs_created_by_id"),
        "verification_runs",
        ["created_by_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_verification_runs_test_suite_id"),
        "verification_runs",
        ["test_suite_id"],
        unique=False,
    )

    op.create_table(
        "verification_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("verification_run_id", sa.Uuid(), nullable=False),
        sa.Column("test_case_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("actual_result", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["test_case_id"], ["test_cases.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["verification_run_id"],
            ["verification_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "verification_run_id",
            "test_case_id",
            name="uq_verification_result_run_case",
        ),
    )
    op.create_index(
        op.f("ix_verification_results_test_case_id"),
        "verification_results",
        ["test_case_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_verification_results_verification_run_id"),
        "verification_results",
        ["verification_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_verification_results_verification_run_id"),
        table_name="verification_results",
    )
    op.drop_index(
        op.f("ix_verification_results_test_case_id"),
        table_name="verification_results",
    )
    op.drop_table("verification_results")
    op.drop_index(
        op.f("ix_verification_runs_test_suite_id"),
        table_name="verification_runs",
    )
    op.drop_index(
        op.f("ix_verification_runs_created_by_id"),
        table_name="verification_runs",
    )
    op.drop_table("verification_runs")
