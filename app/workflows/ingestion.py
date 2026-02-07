import os
import tempfile
from hatchet_sdk import Hatchet
from app.db.session import SessionLocal
from app.db.models import Document
from app.core.storage import minio_client
from app.core.rag import get_vectorstore
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

hatchet = Hatchet()

@hatchet.workflow(on_events=["ingest:document"], name="ingestion-workflow")
class IngestionWorkflow:
    @hatchet.step()
    def process(self, context):
        doc_id = context.workflow_input()["document_id"]
        
        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.id == doc_id).first()
            if not document:
                raise ValueError(f"Document {doc_id} not found")

            document.status = "processing"
            db.commit()

            # Download file
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                local_path = tmp.name
            
            minio_client.download_file(document.minio_path, local_path)

            # Load document
            if document.filename.lower().endswith(".pdf"):
                loader = PyPDFLoader(local_path)
            else:
                loader = TextLoader(local_path)
            
            docs = loader.load()
            
            # Split
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=800,
                chunk_overlap=150,
                separators=["\n\n", "\n", ".", "!", "?", " ", ""],
            )
            chunks = splitter.split_documents(docs)
            
            # Add metadata
            for chunk in chunks:
                chunk.metadata["source"] = document.filename
                chunk.metadata["document_id"] = str(document.id)

            # Vectorize
            vectorstore = get_vectorstore()
            vectorstore.add_documents(chunks)

            # Cleanup
            os.remove(local_path)

            document.status = "completed"
            db.commit()
            
            return {"status": "completed", "chunks": len(chunks)}

        except Exception as e:
            db.rollback()
            if document:
                document.status = "failed"
                document.error_message = str(e)
                db.commit()
            raise e
        finally:
            db.close()
