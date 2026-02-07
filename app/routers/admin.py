from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from hatchet_sdk import Hatchet
from app.db.session import get_session
from app.db.models import Document
from app.core.storage import minio_client
import uuid
import os

router = APIRouter(tags=["admin"])

@router.post("/ingest")
async def trigger_ingest(file: UploadFile = File(...), db: Session = Depends(get_session)):
    """Upload a file and trigger ingestion workflow."""
    try:
        # 1. Upload to MinIO
        file_content = await file.read()
        file_ext = os.path.splitext(file.filename)[1]
        minio_path = f"uploads/{uuid.uuid4()}{file_ext}"
        
        minio_client.upload_bytes(minio_path, file_content, content_type=file.content_type)
        
        # 2. Create DB Record
        doc = Document(
            filename=file.filename,
            minio_path=minio_path,
            status="pending"
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        # 3. Trigger Hatchet
        # Create Hatchet client (ensure HATCHET_CLIENT_TOKEN is set)
        if not os.getenv("HATCHET_CLIENT_TOKEN"):
             # For dev/demo if token not set, we can warn or fail. 
             # Assuming it's set or we rely on default auth.
             pass
             
        hatchet = Hatchet()
        # Trigger via event
        hatchet.event.push(
            "ingest:document",
            {"document_id": str(doc.id)}
        )
        
        return {
            "status": "queued",
            "document_id": doc.id,
            "filename": doc.filename
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
