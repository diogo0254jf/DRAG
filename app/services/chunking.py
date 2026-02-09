"""
Document chunking service.

Supports multiple file types with appropriate chunking strategies
as defined in the Implementation Plan §4.1.
"""
import logging
from typing import Optional

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    MarkdownTextSplitter,
)
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# ── Chunk-size config per content type ──────────────────────────────
CHUNK_CONFIGS: dict[str, dict] = {
    "text/plain":       {"chunk_size": 800,  "chunk_overlap": 200},
    "application/pdf":  {"chunk_size": 1200, "chunk_overlap": 300},
    "text/markdown":    {"chunk_size": 1000, "chunk_overlap": 250},
    "application/json": {"chunk_size": 600,  "chunk_overlap": 100},
    "text/html":        {"chunk_size": 1000, "chunk_overlap": 200},
}

DEFAULT_CHUNK_CONFIG = {"chunk_size": 800, "chunk_overlap": 200}

_EXT_TO_MIME: dict[str, str] = {
    "txt":  "text/plain",
    "pdf":  "application/pdf",
    "md":   "text/markdown",
    "json": "application/json",
    "html": "text/html",
    "htm":  "text/html",
}


# ── Helpers ─────────────────────────────────────────────────────────

def _get_splitter(content_type: str):
    """Select text splitter based on content type."""
    config = CHUNK_CONFIGS.get(content_type, DEFAULT_CHUNK_CONFIG)

    if content_type == "text/markdown":
        return MarkdownTextSplitter(
            chunk_size=config["chunk_size"],
            chunk_overlap=config["chunk_overlap"],
        )

    return RecursiveCharacterTextSplitter(
        chunk_size=config["chunk_size"],
        chunk_overlap=config["chunk_overlap"],
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def detect_content_type(filename: str) -> str:
    """Detect MIME content type from filename extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _EXT_TO_MIME.get(ext, "text/plain")


def _load_file(file_path: str, content_type: str) -> list[Document]:
    """Load file using the appropriate LangChain loader."""
    try:
        if content_type == "application/pdf":
            try:
                from app.services.pdf_parser import VLMPDFParser
                parser = VLMPDFParser()
                text_content = parser.parse(file_path)
                return [Document(page_content=text_content, metadata={"source": file_path})]
            except Exception as e:
                logger.warning(f"VLM Parser failed: {e}. Falling back to PyPDFLoader.")
                from langchain_community.document_loaders import PyPDFLoader
                return PyPDFLoader(file_path).load()

        if content_type == "application/json":
            from langchain_community.document_loaders import JSONLoader
            return JSONLoader(file_path, jq_schema=".", text_content=False).load()

        if content_type in ("text/html",):
            from langchain_community.document_loaders import UnstructuredHTMLLoader
            return UnstructuredHTMLLoader(file_path).load()

        # Default: plain text / markdown
        from langchain_community.document_loaders import TextLoader
        return TextLoader(file_path, encoding="utf-8").load()

    except Exception as exc:
        logger.warning("Loader failed for %s (%s), falling back to raw read: %s",
                        file_path, content_type, exc)
        with open(file_path, "r", errors="replace") as fh:
            return [Document(page_content=fh.read())]


# ── Public API ──────────────────────────────────────────────────────

def load_and_chunk(
    file_path: str,
    filename: str,
    content_type: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> list[Document]:
    """Load a file and split it into chunks.

    Args:
        file_path:    Local path to the downloaded file.
        filename:     Original filename (used for type detection).
        content_type: MIME type override.  Auto-detected if None.
        metadata:     Extra metadata to attach to every chunk.

    Returns:
        List of LangChain Document chunks ready for embedding.
    """
    if content_type is None:
        content_type = detect_content_type(filename)

    docs = _load_file(file_path, content_type)

    splitter = _get_splitter(content_type)
    chunks = splitter.split_documents(docs)

    base_meta: dict = {"source": filename, "content_type": content_type}
    if metadata:
        base_meta.update(metadata)

    for idx, chunk in enumerate(chunks):
        chunk.metadata.update(base_meta)
        chunk.metadata["chunk_index"] = idx

    logger.info("Chunked '%s' → %d chunks  (type=%s)", filename, len(chunks), content_type)
    return chunks


def chunk_text(
    text: str,
    filename: str = "unknown",
    content_type: str = "text/plain",
    metadata: Optional[dict] = None,
) -> list[Document]:
    """Chunk raw text directly (no file needed)."""
    doc = Document(page_content=text, metadata={"source": filename})
    splitter = _get_splitter(content_type)
    chunks = splitter.split_documents([doc])

    base_meta: dict = {"source": filename, "content_type": content_type}
    if metadata:
        base_meta.update(metadata)

    for idx, chunk in enumerate(chunks):
        chunk.metadata.update(base_meta)
        chunk.metadata["chunk_index"] = idx

    return chunks
