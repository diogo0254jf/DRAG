"""add required_placeholders

Revision ID: 20260205_0002
Revises: 20260205_0001
Create Date: 2026-02-05 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260205_0002"
down_revision = "20260205_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE prompts "
        "ADD COLUMN IF NOT EXISTS required_placeholders JSONB "
        "NOT NULL DEFAULT '[]'::jsonb"
    )
    op.alter_column("prompts", "required_placeholders", server_default=None)


def downgrade() -> None:
    op.execute("ALTER TABLE prompts DROP COLUMN IF EXISTS required_placeholders")
