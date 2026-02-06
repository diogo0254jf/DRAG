"""add conversation memory

Revision ID: 20260205_0003
Revises: 20260205_0002
Create Date: 2026-02-05 00:00:00

"""
from alembic import op
import sqlalchemy as sa

revision = "20260205_0003"
down_revision = "20260205_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("conversations", sa.Column("topic", sa.String(length=200), nullable=True))
    op.add_column("conversations", sa.Column("memory_updated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("conversations", "memory_updated_at")
    op.drop_column("conversations", "topic")
    op.drop_column("conversations", "summary")
