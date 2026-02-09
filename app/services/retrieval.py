"""
Hybrid retrieval service combining semantic and keyword search.

Implements Reciprocal Rank Fusion (RRF) as defined in §4.2 of the
Implementation Plan.
"""
import logging
from typing import Optional

from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# RRF constant (standard value from the original paper)
RRF_K = 60


def retrieve_context(
    retriever,
    query: str,
    k: int = 4,
    db_session=None,
) -> tuple[str, list[Document]]:
    """Retrieve context using hybrid search when possible.

    Falls back to semantic-only if keyword search is unavailable.

    Args:
        retriever:  LangChain retriever (PGVector-based).
        query:      User query string.
        k:          Number of results to return.
        db_session: Optional SQLAlchemy session for keyword search.

    Returns:
        Tuple of (formatted context string, list of source Documents).
    """
    # ── Semantic search ─────────────────────────────────────────────
    try:
        semantic_docs = retriever.invoke(query)
    except Exception as exc:
        logger.error("Semantic search failed: %s", exc)
        semantic_docs = []

    # ── Keyword search (requires a db session) ─────────────────────
    keyword_docs: list[Document] = []
    if db_session is not None:
        try:
            keyword_docs = _keyword_search(db_session, query, k=k)
        except Exception as exc:
            logger.debug("Keyword search unavailable: %s", exc)

    # ── Fuse results ────────────────────────────────────────────────
    if semantic_docs and keyword_docs:
        fused = _reciprocal_rank_fusion([semantic_docs, keyword_docs], k=k)
    elif semantic_docs:
        fused = semantic_docs[:k]
    elif keyword_docs:
        fused = keyword_docs[:k]
    else:
        return "", []

    context = "\n\n".join(doc.page_content for doc in fused)
    return context, fused


# ── Private helpers ─────────────────────────────────────────────────

def _keyword_search(
    db_session,
    query: str,
    k: int = 4,
) -> list[Document]:
    """Full-text search using PostgreSQL tsvector / tsquery.

    Operates on the ``langchain_pg_embedding`` table created by PGVector.
    Returns empty list gracefully if the index or column is missing.
    """
    from sqlalchemy import text

    sql = text("""
        SELECT document, cmetadata,
               ts_rank_cd(
                   to_tsvector('english', document),
                   websearch_to_tsquery('english', :query)
               ) AS rank
        FROM langchain_pg_embedding
        WHERE to_tsvector('english', document)
           @@ websearch_to_tsquery('english', :query)
        ORDER BY rank DESC
        LIMIT :limit
    """)

    try:
        rows = db_session.execute(sql, {"query": query, "limit": k}).fetchall()
    except Exception as exc:
        logger.debug("Keyword search query failed: %s", exc)
        return []

    return [
        Document(page_content=row[0], metadata=row[1] or {})
        for row in rows
    ]


def _reciprocal_rank_fusion(
    doc_lists: list[list[Document]],
    k: int = 4,
) -> list[Document]:
    """Combine multiple ranked lists using Reciprocal Rank Fusion.

    ``RRF_score = Σ  1 / (RRF_K + rank)``  across all lists.
    """
    scores: dict[int, float] = {}
    doc_map: dict[int, Document] = {}

    for doc_list in doc_lists:
        for rank, doc in enumerate(doc_list):
            key = hash(doc.page_content)
            if key not in doc_map:
                doc_map[key] = doc
                scores[key] = 0.0
            scores[key] += 1.0 / (RRF_K + rank + 1)

    sorted_keys = sorted(scores, key=scores.get, reverse=True)  # type: ignore[arg-type]
    return [doc_map[key] for key in sorted_keys[:k]]
