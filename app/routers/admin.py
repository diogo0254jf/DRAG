from fastapi import APIRouter, HTTPException
from hatchet_sdk import Hatchet
from pydantic import BaseModel
import os

router = APIRouter(tags=["admin"])
# Hatchet client will be initialized lazily

class IngestResponse(BaseModel):
    status: str
    workflow_run_id: str

@router.post("/ingest", response_model=IngestResponse)
async def trigger_ingest():
    """Trigger the document ingestion workflow asynchronously."""
    # Lazy init to verify configuration only when used
    if not os.getenv("HATCHET_CLIENT_TOKEN"):
        raise HTTPException(
            status_code=503, 
            detail="Hatchet is not configured. Please set HATCHET_CLIENT_TOKEN environment variable."
        )
        
    try:
        hatchet = Hatchet()
        # Push event to trigger workflow
        workflow_run_id = hatchet.admin.run_workflow("IngestionWorkflow", {})
        
        return IngestResponse(
            status="ingestion_triggered",
            workflow_run_id=workflow_run_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
