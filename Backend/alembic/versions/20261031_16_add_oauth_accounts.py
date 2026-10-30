"""Add OAuth accounts and authorization state.

Revision ID: 20261031_16
Revises: 20260912_15
"""

from alembic import op
import sqlalchemy as sa

revision = "20261031_16"
down_revision = "20260912_15"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=True)
    op.create_table(
        "oauth_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_oauth_account_provider_user"),
    )
    op.create_index(op.f("ix_oauth_accounts_user_id"), "oauth_accounts", ["user_id"], unique=False)
    op.create_table(
        "oauth_authorizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("state", sa.String(length=128), nullable=False),
        sa.Column("code_verifier", sa.String(length=128), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exchange_code_hash", sa.String(length=64), nullable=True),
        sa.Column("exchange_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("state"),
        sa.UniqueConstraint("exchange_code_hash"),
    )
    op.create_index(op.f("ix_oauth_authorizations_state"), "oauth_authorizations", ["state"], unique=True)
    op.create_index(op.f("ix_oauth_authorizations_expires_at"), "oauth_authorizations", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_oauth_authorizations_expires_at"), table_name="oauth_authorizations")
    op.drop_index(op.f("ix_oauth_authorizations_state"), table_name="oauth_authorizations")
    op.drop_table("oauth_authorizations")
    op.drop_index(op.f("ix_oauth_accounts_user_id"), table_name="oauth_accounts")
    op.drop_table("oauth_accounts")
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=False)
