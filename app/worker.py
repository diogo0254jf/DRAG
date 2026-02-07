from hatchet_sdk import Hatchet
from dotenv import load_dotenv

# Load env vars
load_dotenv()

from app.workflows.ingestion import ingestion_workflow

def main():
    hatchet = Hatchet()
    worker = hatchet.worker("ingestion-worker")
    worker.register_workflow(ingestion_workflow)
    worker.start()

if __name__ == "__main__":
    main()

