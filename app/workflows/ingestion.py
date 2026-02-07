from hatchet_sdk import Hatchet
from app.db.session import SessionLocal
from app.db.models import Document
from app.core.storage import minio_client
from app.services.r2r_client import R2RClient
import os
import logging

logger = logging.getLogger(__name__)

hatchet = Hatchet()

# Define the workflow object
ingestion_workflow = hatchet.workflow(
    name="ingestion-workflow",
    on_events=["ingest:document"]
)

@ingestion_workflow.task()
def process(context):
    doc_id = context.workflow_input()["document_id"]
    
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == doc_id).first()
        if not document:
            raise ValueError(f"Document {doc_id} not found")
        
        logger.info(f"Processing document: {document.filename}")
        
        # Update progress
        document.status = "processing"
        db.commit()
        
        # 1. Download from MinIO
        content = minio_client.get_object(document.minio_path)
        
        # 2. Ingest into R2R
        r2r = R2RClient()
        # Use filename as title, pass doc_id in metadata
        ingest_resp = r2r.ingest_file(
            file_content=content,
            file_name=document.filename,
            document_id=str(document.id)
        )
        
        # 3. Update Status
        document.status = "completed"
        # Store distal R2R document ID if available
        if isinstance(ingest_resp, dict) and "document_id" in ingest_resp:
             document.r2r_id = ingest_resp["document_id"]
             
        db.commit()
        
        return {
            "status": "success",
            "document_id": doc_id,
            "r2r_id": getattr(document, 'r2r_id', None)
        }

    except Exception as e:
        logger.error(f"Error processing document {doc_id}: {str(e)}")
        if db:
            db.rollback()
            document = db.query(Document).filter(Document.id == doc_id).first()
            if document:
                document.status = "failed"
                document.error_message = str(e)
                db.commit()
        raise e
    finally:
        db.close()
