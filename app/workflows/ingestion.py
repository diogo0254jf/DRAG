"""Ingestion workflow: download, parse, chunk, embed and store in PGVector."""
import logging
import os
import tempfile

from hatchet_sdk import Hatchet, Context
from pydantic import BaseModel

from app.core.rag import get_vectorstore
from app.core.storage import minio_client
from app.db.models import Document
from app.db.session import SessionLocal
from app.services.chunking import load_and_chunk

logger = logging.getLogger(__name__)

hatchet = Hatchet()


class DocumentInput(BaseModel):
    """Input model for document ingestion workflow."""
    document_id: str


# Define the workflow object with input validator
ingestion_workflow = hatchet.workflow(
    name="ingestion-workflow",
    on_events=["ingest:document"],
    input_validator=DocumentInput,
)


@ingestion_workflow.task()
def process(input: DocumentInput, context: Context):
    doc_id = input.document_id

    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == doc_id).first()
        if not document:
            raise ValueError(f"Document {doc_id} not found")

        logger.info("Processing document: %s", document.filename)

        # Update progress
        document.status = "processing"
        db.commit()

        # 1. Download from MinIO to a temp file
        suffix = os.path.splitext(document.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            minio_client.download_file(document.minio_path, tmp.name)
            local_path = tmp.name

        try:
            # 2. Chunk the document
            chunks = load_and_chunk(
                file_path=local_path,
                filename=document.filename,
                metadata={"document_id": str(document.id)},
            )

            if not chunks:
                raise ValueError(f"No chunks produced from {document.filename}")

            logger.info("Produced %d chunks from %s", len(chunks), document.filename)

            # 3. Embed and store in PGVector
            vectorstore = get_vectorstore()
            vectorstore.add_documents(chunks)
            logger.info("Stored %d chunks in vectorstore", len(chunks))

            # 4. Optionally forward to R2R as well
            r2r_id = None
            try:
                from app.services.r2r_client import R2RClient

                r2r = R2RClient()
                with open(local_path, "rb") as fh:
                    content = fh.read()
                ingest_resp = r2r.ingest_file(
                    file_content=content,
                    file_name=document.filename,
                    document_id=str(document.id),
                )
                if isinstance(ingest_resp, dict) and "document_id" in ingest_resp:
                    document.r2r_id = ingest_resp["document_id"]
                    r2r_id = document.r2r_id
            except Exception as r2r_err:
                logger.warning("R2R ingestion skipped: %s", r2r_err)

            # 5. Update document status
            document.status = "completed"
            document.chunk_count = len(chunks)
            db.commit()

            return {
                "status": "success",
                "document_id": doc_id,
                "chunks": len(chunks),
                "r2r_id": r2r_id,
            }

        finally:
            if os.path.exists(local_path):
                os.unlink(local_path)

    except Exception as e:
        logger.error("Error processing document %s: %s", doc_id, e)
        if db:
            db.rollback()
            document = db.query(Document).filter(Document.id == doc_id).first()
            if document:
                document.status = "failed"
                document.error_message = str(e)
                db.commit()
        raise
    finally:
        db.close()
