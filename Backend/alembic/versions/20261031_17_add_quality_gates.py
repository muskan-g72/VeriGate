"""Add project quality gates and run evaluations.

Revision ID: 20261031_17
Revises: 20261031_16
"""
from alembic import op
import sqlalchemy as sa

revision = "20261031_17"
down_revision = "20261031_16"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("quality_gates",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("min_pass_rate_enabled", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("min_pass_rate", sa.Float(), nullable=True),
        sa.Column("critical_tests_enabled", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("critical_priorities", sa.JSON(), nullable=False),
        sa.Column("critical_issues_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("min_executed_tests_enabled", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("min_executed_tests", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("treat_blocked_as_failure", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("updated_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("project_id"))
    op.create_index(op.f("ix_quality_gates_project_id"), "quality_gates", ["project_id"])
    op.create_table("quality_gate_evaluations",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("run_id", sa.Uuid(), nullable=False), sa.Column("gate_id", sa.Uuid(), nullable=True),
        sa.Column("outcome", sa.String(length=20), nullable=False), sa.Column("rules_snapshot", sa.JSON(), nullable=False), sa.Column("rule_results", sa.JSON(), nullable=False), sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["run_id"], ["verification_runs.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["gate_id"], ["quality_gates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("run_id"))
    op.create_index(op.f("ix_quality_gate_evaluations_run_id"), "quality_gate_evaluations", ["run_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_quality_gate_evaluations_run_id"), table_name="quality_gate_evaluations")
    op.drop_table("quality_gate_evaluations")
    op.drop_index(op.f("ix_quality_gates_project_id"), table_name="quality_gates")
    op.drop_table("quality_gates")
