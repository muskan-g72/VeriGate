"""Add scheduled verification runs.

Revision ID: 20261102_23
Revises: 20261102_22
"""
from alembic import op
import sqlalchemy as sa

revision = "20261102_23"
down_revision = "20261102_22"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("scheduled_runs", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("test_suite_id", sa.Uuid(), nullable=False), sa.Column("created_by_id", sa.Uuid(), nullable=False), sa.Column("name", sa.String(length=160), nullable=False), sa.Column("interval_minutes", sa.Integer(), nullable=False), sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False), sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True), sa.Column("last_run_id", sa.Uuid(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["last_run_id"], ["verification_runs.id"], ondelete="SET NULL"), sa.ForeignKeyConstraint(["test_suite_id"], ["test_suites.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"))
    op.create_index(op.f("ix_scheduled_runs_test_suite_id"), "scheduled_runs", ["test_suite_id"])
    op.create_index(op.f("ix_scheduled_runs_created_by_id"), "scheduled_runs", ["created_by_id"])
    op.create_index(op.f("ix_scheduled_runs_next_run_at"), "scheduled_runs", ["next_run_at"])

def downgrade() -> None:
    op.drop_index(op.f("ix_scheduled_runs_next_run_at"), table_name="scheduled_runs")
    op.drop_index(op.f("ix_scheduled_runs_created_by_id"), table_name="scheduled_runs")
    op.drop_index(op.f("ix_scheduled_runs_test_suite_id"), table_name="scheduled_runs")
    op.drop_table("scheduled_runs")
