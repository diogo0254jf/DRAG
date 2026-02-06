# from hatchet_sdk import Hatchet
# from app.core.rag import index_docs
# import logging

# # Configure basic logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# hatchet = Hatchet(debug=True)

# @hatchet.workflow(name="ingest-docs", on_events=["ingest-docs"])
# class IngestionWorkflow:
#     @hatchet.step()
#     def load_and_index(self, context):
#         """Step to load and index documents."""
#         logger.info("Starting document ingestion...")
#         try:
#             # Re-run index_docs logic
#             # Note: This might block the worker thread, which is fine for a worker process
#             vectorstore = index_docs()
            
#             if vectorstore:
#                 doc_count = vectorstore.index.ntotal
#                 return {
#                     "status": "completed", 
#                     "message": f"Successfully indexed documents. Total vectors: {doc_count}"
#                 }
#             else:
#                 return {
#                     "status": "warning",
#                     "message": "No documents found or indexing failed."
#                 }
#         except Exception as e:
#             logger.error(f"Error during ingestion: {e}")
#             raise e

# def start_worker():
#     """Start the Hatchet worker."""
#     logger.info("Starting Hatchet worker 'ingestion-worker'...")
#     worker = hatchet.worker("ingestion-worker", max_runs=1)
#     worker.register_workflow(IngestionWorkflow())
#     worker.start()

# if __name__ == "__main__":
#     start_worker()
