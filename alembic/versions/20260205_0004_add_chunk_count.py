"""add chunk_count to documents

Revision ID: 20260205_0004
Revises: 20260205_0003
Create Date: 2026-02-09 00:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = "20260205_0004"
down_revision = "20260205_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("chunk_count", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("documents", "chunk_count")
