"""Add GitHub PR verification fields to projects and verification_runs.

Revision ID: 20260912_15
Revises: 20260908_14
Create Date: 2026-09-12
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260912_15"
down_revision: str | Sequence[str] | None = "20260908_14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Projects table changes
    op.add_column(
        "projects",
        sa.Column("github_repo", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column(
            "github_default_branch",
            sa.String(length=100),
            server_default=sa.text("'main'"),
            nullable=True,
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "github_verification_enabled",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
    )
    op.add_column(
        "projects",
        sa.Column("github_webhook_secret", sa.String(length=255), nullable=True),
    )
    op.create_index(
        op.f("ix_projects_github_repo"),
        "projects",
        ["github_repo"],
        unique=False,
    )

    # 2. Verification runs table changes
    op.add_column(
        "verification_runs",
        sa.Column(
            "trigger_source",
            sa.String(length=50),
            server_default=sa.text("'manual'"),
            nullable=False,
        ),
    )
    op.add_column(
        "verification_runs",
        sa.Column("pr_number", sa.Integer(), nullable=True),
    )
    op.add_column(
        "verification_runs",
        sa.Column("pr_title", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "verification_runs",
        sa.Column("pr_source_branch", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "verification_runs",
        sa.Column("pr_target_branch", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "verification_runs",
        sa.Column("pr_commit_sha", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "verification_runs",
        sa.Column("pr_repository", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "verification_runs",
        sa.Column("pr_author", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "verification_runs",
        sa.Column("pr_url", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "verification_runs",
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
    )
    op.create_index(
        op.f("ix_verification_runs_pr_commit_sha"),
        "verification_runs",
        ["pr_commit_sha"],
        unique=False,
    )
    op.create_index(
        op.f("ix_verification_runs_idempotency_key"),
        "verification_runs",
        ["idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_verification_runs_idempotency_key"),
        table_name="verification_runs",
    )
    op.drop_index(
        op.f("ix_verification_runs_pr_commit_sha"),
        table_name="verification_runs",
    )
    op.drop_column("verification_runs", "idempotency_key")
    op.drop_column("verification_runs", "pr_url")
    op.drop_column("verification_runs", "pr_author")
    op.drop_column("verification_runs", "pr_repository")
    op.drop_column("verification_runs", "pr_commit_sha")
    op.drop_column("verification_runs", "pr_target_branch")
    op.drop_column("verification_runs", "pr_source_branch")
    op.drop_column("verification_runs", "pr_title")
    op.drop_column("verification_runs", "pr_number")
    op.drop_column("verification_runs", "trigger_source")

    op.drop_index(op.f("ix_projects_github_repo"), table_name="projects")
    op.drop_column("projects", "github_webhook_secret")
    op.drop_column("projects", "github_verification_enabled")
    op.drop_column("projects", "github_default_branch")
    op.drop_column("projects", "github_repo")
