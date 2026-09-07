"""Create team_members table.

Revision ID: 20260907_11
Revises: 20260907_10
Create Date: 2026-09-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260907_11"
down_revision: str | Sequence[str] | None = "20260907_10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "team_members",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("team_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "role",
            sa.String(length=20),
            server_default=sa.text("'member'"),
            nullable=False,
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_member_team_user"),
    )
    for column_name in ("team_id", "user_id"):
        op.create_index(
            op.f(f"ix_team_members_{column_name}"),
            "team_members",
            [column_name],
            unique=False,
        )


def downgrade() -> None:
    for column_name in ("user_id", "team_id"):
        op.drop_index(op.f(f"ix_team_members_{column_name}"), table_name="team_members")
    op.drop_table("team_members")
