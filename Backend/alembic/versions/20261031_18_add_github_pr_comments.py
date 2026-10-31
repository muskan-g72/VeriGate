"""Add PR summary comment configuration and publication state.

Revision ID: 20261031_18
Revises: 20261031_17
"""
from alembic import op
import sqlalchemy as sa

revision = "20261031_18"
down_revision = "20261031_17"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("pr_comments_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("projects", sa.Column("comment_include_ai", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("projects", sa.Column("comment_max_failures", sa.Integer(), nullable=False, server_default="10"))
    op.add_column("verification_runs", sa.Column("comment_status", sa.String(length=20), nullable=True))
    op.add_column("verification_runs", sa.Column("comment_url", sa.String(length=500), nullable=True))
    op.add_column("verification_runs", sa.Column("comment_error", sa.String(length=500), nullable=True))
    op.create_table(
        "github_pr_comments",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("repository", sa.String(length=255), nullable=False), sa.Column("pr_number", sa.Integer(), nullable=False),
        sa.Column("github_comment_id", sa.Integer(), nullable=True), sa.Column("comment_url", sa.String(length=500), nullable=True),
        sa.Column("last_run_id", sa.Uuid(), nullable=True), sa.Column("last_status", sa.String(length=20), nullable=False), sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["last_run_id"], ["verification_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("project_id", "repository", "pr_number", name="uq_github_pr_comment_project_repo_pr"),
    )
    op.create_index(op.f("ix_github_pr_comments_project_id"), "github_pr_comments", ["project_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_github_pr_comments_project_id"), table_name="github_pr_comments")
    op.drop_table("github_pr_comments")
    op.drop_column("verification_runs", "comment_error")
    op.drop_column("verification_runs", "comment_url")
    op.drop_column("verification_runs", "comment_status")
    op.drop_column("projects", "comment_max_failures")
    op.drop_column("projects", "comment_include_ai")
    op.drop_column("projects", "pr_comments_enabled")
