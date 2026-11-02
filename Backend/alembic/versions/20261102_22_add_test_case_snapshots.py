"""Store immutable test-case definitions on verification results.

Revision ID: 20261102_22
Revises: 20261102_21
"""

from alembic import op
import sqlalchemy as sa


revision = "20261102_22"
down_revision = "20261102_21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("verification_results", sa.Column("test_case_snapshot", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("verification_results", "test_case_snapshot")
