"""Add a per-project GitHub access token.

Revision ID: 20261102_20
Revises: 20261101_19
"""

from alembic import op
import sqlalchemy as sa


revision = "20261102_20"
down_revision = "20261101_19"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("github_token", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "github_token")
