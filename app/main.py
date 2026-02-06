import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import FAISS_PATH, PROMPT_SEED_PATH, HISTORY_MAX_MESSAGES
from app.core.rag import build_llm, build_retriever, index_docs, load_vectorstore
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.routers import chat, conversations, health, prompts
from app.services.prompts import seed_prompts
from app.services.chat_graph import build_chat_graph

app = FastAPI(title="RAG API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.on_event("startup")
def startup() -> None:
    """Initialize application resources on startup."""
    Base.metadata.create_all(bind=engine)

    # Load or create vectorstore
    if os.path.exists(FAISS_PATH):
        vectorstore = load_vectorstore()
    else:
        vectorstore = index_docs()
        if vectorstore is None:
            raise RuntimeError("No documents found in docs/ to build the index.")

    # Store resources in app state
    app.state.vectorstore = vectorstore
    app.state.retriever = build_retriever(vectorstore)
    app.state.llm = build_llm()
    
    # Build chat graph with dependencies
    app.state.chat_graph = build_chat_graph(
        llm=app.state.llm,
        retriever=app.state.retriever,
        db_session_factory=SessionLocal,
        max_messages=HISTORY_MAX_MESSAGES,
    )

    # Seed prompts
    db = SessionLocal()
    try:
        seed_prompts(db, PROMPT_SEED_PATH)
    finally:
        db.close()


app.include_router(health.router)
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(prompts.router)

