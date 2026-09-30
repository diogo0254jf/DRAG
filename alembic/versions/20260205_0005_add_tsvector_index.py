"""add tsvector GIN index for hybrid search

Revision ID: 20260205_0005
Revises: 20260205_0004
Create Date: 2026-02-09 00:00:00

Adds a GIN index on the langchain_pg_embedding.document column to enable
fast full-text keyword search for hybrid retrieval.
"""
from alembic import op

revision = "20260205_0005"
down_revision = "20260205_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_embedding_document_tsv
        ON langchain_pg_embedding
        USING gin(to_tsvector('english', document))
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_embedding_document_tsv")
