"""Create requirements and traceability associations.

Revision ID: 20261102_21
Revises: 20261102_20
"""

from alembic import op
import sqlalchemy as sa


revision = "20261102_21"
down_revision = "20261102_20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "requirements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("requirement_key", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("category", sa.String(length=30), nullable=False, server_default="functional"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "requirement_key", name="uq_requirement_project_key"),
    )
    op.create_index(op.f("ix_requirements_project_id"), "requirements", ["project_id"])
    op.create_index(op.f("ix_requirements_priority"), "requirements", ["priority"])
    op.create_index(op.f("ix_requirements_category"), "requirements", ["category"])
    op.create_index(op.f("ix_requirements_status"), "requirements", ["status"])
    op.create_table(
        "requirement_test_cases",
        sa.Column("requirement_id", sa.Uuid(), nullable=False),
        sa.Column("test_case_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["requirement_id"], ["requirements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["test_case_id"], ["test_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("requirement_id", "test_case_id"),
    )
    op.create_table(
        "issue_requirements",
        sa.Column("issue_id", sa.Uuid(), nullable=False),
        sa.Column("requirement_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requirement_id"], ["requirements.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("issue_id", "requirement_id"),
    )


def downgrade() -> None:
    op.drop_table("issue_requirements")
    op.drop_table("requirement_test_cases")
    op.drop_index(op.f("ix_requirements_status"), table_name="requirements")
    op.drop_index(op.f("ix_requirements_category"), table_name="requirements")
    op.drop_index(op.f("ix_requirements_priority"), table_name="requirements")
    op.drop_index(op.f("ix_requirements_project_id"), table_name="requirements")
    op.drop_table("requirements")
