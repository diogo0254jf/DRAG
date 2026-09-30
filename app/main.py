import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import PROMPT_SEED_PATH, HISTORY_MAX_MESSAGES, DATABASE_URL
from app.core.rag import build_llm, build_retriever, get_vectorstore
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.routers import chat, conversations, health, prompts, admin
from app.services.prompts import seed_prompts
from app.services.chat_graph import build_chat_graph

app = FastAPI(title="RAG API", version="0.3.0")
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

    # Initialize vectorstore (connection only)
    vectorstore = get_vectorstore()

    # Store resources in app state
    app.state.vectorstore = vectorstore
    app.state.retriever = build_retriever(vectorstore)
    app.state.llm = build_llm()
    
    # Init checkpointer — prefer PostgresSaver in production
    checkpointer = _build_checkpointer()

    # Build chat graph with dependencies
    app.state.chat_graph = build_chat_graph(
        llm=app.state.llm,
        retriever=app.state.retriever,
        db_session_factory=SessionLocal,
        max_messages=HISTORY_MAX_MESSAGES,
        checkpointer=checkpointer,
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
app.include_router(admin.router)


def _build_checkpointer():
    """Build the best available checkpointer.

    Prefers PostgresSaver and falls back to SqliteSaver.
    """
    if DATABASE_URL:
        try:
            from langgraph.checkpoint.postgres import PostgresSaver

            checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
            checkpointer.setup()
            return checkpointer
        except Exception:
            pass  # fall through to SQLite

    from langgraph.checkpoint.sqlite import SqliteSaver
    import sqlite3

    conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
    return SqliteSaver(conn)
