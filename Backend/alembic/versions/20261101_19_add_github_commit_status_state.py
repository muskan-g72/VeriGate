"""Store GitHub commit-status publication state.

Revision ID: 20261101_19
Revises: 20261031_18
"""

from alembic import op
import sqlalchemy as sa


revision = "20261101_19"
down_revision = "20261031_18"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("verification_runs", sa.Column("commit_status", sa.String(length=20), nullable=True))
    op.add_column("verification_runs", sa.Column("commit_status_url", sa.String(length=500), nullable=True))
    op.add_column("verification_runs", sa.Column("commit_status_error", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("verification_runs", "commit_status_error")
    op.drop_column("verification_runs", "commit_status_url")
    op.drop_column("verification_runs", "commit_status")
