"""Add evidence and verification investigation fields.

Revision ID: 20260907_07
Revises: 20260819_06
Create Date: 2026-09-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260907_07"
down_revision: str | Sequence[str] | None = "20260819_06"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "verification_results",
        sa.Column("failure_message", sa.Text(), nullable=True),
    )
    op.add_column(
        "verification_results",
        sa.Column("stack_trace", sa.Text(), nullable=True),
    )
    op.add_column(
        "verification_results",
        sa.Column("duration", sa.Float(), nullable=True),
    )

    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("verification_result_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["verification_result_id"],
            ["verification_results.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_evidence_verification_result_id"),
        "evidence",
        ["verification_result_id"],
        unique=False,
    )

    op.add_column(
        "issues",
        sa.Column("test_case_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "issues",
        sa.Column("verification_run_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "issues",
        sa.Column("assigned_to_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "issues",
        sa.Column(
            "priority",
            sa.String(length=20),
            server_default=sa.text("'medium'"),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_issues_test_case_id",
        "issues",
        "test_cases",
        ["test_case_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_issues_verification_run_id",
        "issues",
        "verification_runs",
        ["verification_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_issues_assigned_to_id",
        "issues",
        "users",
        ["assigned_to_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_issues_test_case_id"),
        "issues",
        ["test_case_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_issues_verification_run_id"),
        "issues",
        ["verification_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_issues_assigned_to_id"),
        "issues",
        ["assigned_to_id"],
        unique=False,
    )

    op.execute(
        """
        UPDATE issues
        SET
            test_case_id = verification_results.test_case_id,
            verification_run_id = verification_results.verification_run_id
        FROM verification_results
        WHERE issues.verification_result_id = verification_results.id
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_issues_assigned_to_id"), table_name="issues")
    op.drop_index(op.f("ix_issues_verification_run_id"), table_name="issues")
    op.drop_index(op.f("ix_issues_test_case_id"), table_name="issues")
    op.drop_constraint("fk_issues_assigned_to_id", "issues", type_="foreignkey")
    op.drop_constraint("fk_issues_verification_run_id", "issues", type_="foreignkey")
    op.drop_constraint("fk_issues_test_case_id", "issues", type_="foreignkey")
    op.drop_column("issues", "priority")
    op.drop_column("issues", "assigned_to_id")
    op.drop_column("issues", "verification_run_id")
    op.drop_column("issues", "test_case_id")

    op.drop_index(op.f("ix_evidence_verification_result_id"), table_name="evidence")
    op.drop_table("evidence")

    op.drop_column("verification_results", "duration")
    op.drop_column("verification_results", "stack_trace")
    op.drop_column("verification_results", "failure_message")
