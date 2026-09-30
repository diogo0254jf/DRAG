"""
Chat Graph using LangGraph StateGraph.

This module implements the chat flow as a graph with nodes for:
- prepare_context: Build history and memory context
- retrieve: Get relevant documents from vectorstore
- generate: Generate response using LLM
- update_memory: Update conversation memory periodically
"""
from typing import Annotated, Optional, Sequence
from dataclasses import dataclass, field

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from app.db.models import Conversation, Message
from app.services.conversations import (
    get_recent_messages,
    get_trimmed_messages,
    format_history,
)
from app.services.memory import build_memory_text, update_conversation_memory, MemoryPromptMissing
from app.services.prompt_builder import (
    build_rag_prompt,
    build_no_context_prompt,
    PromptNotConfigured,
    PromptRenderError,
)
from app.services.retrieval import retrieve_context


@dataclass
class ChatState:
    """State for the chat graph."""
    # Input
    conversation_id: str
    user_message: str
    
    # Context
    history_text: str = ""
    memory_text: str = ""
    context: str = ""
    
    # Output
    response: str = ""
    
    # Internal
    should_retrieve: bool = False
    should_update_memory: bool = False
    error: Optional[str] = None


def create_prepare_context_node(db_session_factory, max_messages: int = 30):
    """Create the prepare_context node with database access."""
    
    def prepare_context(state: ChatState) -> dict:
        """Prepare history and memory context for the LLM."""
        import uuid
        from app.services.conversations import get_conversation
        
        db = db_session_factory()
        try:
            conv_id = uuid.UUID(state.conversation_id)
            conversation = get_conversation(db, conv_id)
            
            if not conversation:
                return {"error": "Conversation not found"}
            
            # Get and trim messages
            messages = get_recent_messages(db, conv_id, max_messages)
            trimmed = get_trimmed_messages(messages, max_tokens=2000)
            history_text = format_history(trimmed)
            
            # Get memory context
            memory_text = build_memory_text(conversation)
            
            # Check if we should update memory
            total_messages = len(messages)
            from app.core.config import MEMORY_UPDATE_EVERY
            should_update = MEMORY_UPDATE_EVERY > 0 and total_messages % MEMORY_UPDATE_EVERY == 0
            
            return {
                "history_text": history_text,
                "memory_text": memory_text,
                "should_update_memory": should_update,
            }
        finally:
            db.close()
    
    return prepare_context


def create_retrieve_node(retriever, db_session_factory=None):
    """Create the retrieve node with hybrid search support."""

    def retrieve(state: ChatState) -> dict:
        """Retrieve relevant documents using hybrid search."""
        if state.error:
            return {}

        db_session = None
        if db_session_factory:
            db_session = db_session_factory()

        try:
            context, _ = retrieve_context(
                retriever,
                state.user_message,
                db_session=db_session,
            )
            return {"context": context or ""}
        finally:
            if db_session:
                db_session.close()

    return retrieve


def create_generate_node(llm, db_session_factory):
    """Create the generate node with LLM access."""
    
    def generate(state: ChatState) -> dict:
        """Generate response using the LLM."""
        if state.error:
            return {"response": f"Error: {state.error}"}
        
        db = db_session_factory()
        try:
            # Build appropriate prompt based on context
            if state.context:
                prompt = build_rag_prompt(
                    db,
                    state.user_message,
                    state.context,
                    state.history_text,
                    state.memory_text,
                )
            else:
                prompt = build_no_context_prompt(
                    db,
                    state.user_message,
                    state.history_text,
                    state.memory_text,
                )
            
            response = llm.invoke(prompt)
            return {"response": response.content}
        except (PromptNotConfigured, PromptRenderError) as e:
            return {"error": str(e), "response": f"Error: {e}"}
        finally:
            db.close()
    
    return generate


def create_update_memory_node(llm, db_session_factory):
    """Create the update_memory node."""
    
    def update_memory(state: ChatState) -> dict:
        """Update conversation memory if needed."""
        if not state.should_update_memory or state.error:
            return {}
        
        import uuid
        from app.services.conversations import get_conversation
        
        db = db_session_factory()
        try:
            conv_id = uuid.UUID(state.conversation_id)
            conversation = get_conversation(db, conv_id)
            
            if conversation:
                try:
                    update_conversation_memory(
                        db,
                        conversation,
                        llm,
                        state.history_text,
                    )
                except MemoryPromptMissing:
                    pass
        finally:
            db.close()
        
        return {}
    
    return update_memory



@dataclass
class RouteQuery(BaseModel):
    """Route decision for the query."""
    action: str = Field(
        description="Action to take: 'retrieve' if documents are needed, 'no_retrieve' for smalltalk/general knowledge",
        pattern="^(retrieve|no_retrieve)$"
    )

def create_route_node(llm):
    """Create the route node."""
    
    def route_query(state: ChatState) -> dict:
        """Decide whether to retrieve documents or not."""
        if state.error:
            return {"should_retrieve": False}
        
        # Simple routing heuristic fallback if LLM fails
        # If query has > 5 words, assume it might need context
        heuristic_decision = len(state.user_message.split()) > 5
        
        try:
            structured_llm = llm.with_structured_output(RouteQuery)
            decision = structured_llm.invoke(
                f"Analise a pergunta do usuário e decida se é necessário buscar documentos para responder.\n"
                f"Pergunta: {state.user_message}\n"
                f"Responda 'retrieve' se precisar de contexto específico, 'no_retrieve' se for conversa fiada ou conhecimento geral."
            )
            should_retrieve = decision.action == "retrieve"
        except Exception:
            should_retrieve = heuristic_decision
            
        return {"should_retrieve": should_retrieve}
        
    return route_query

def condition_routing(state: ChatState) -> str:
    """Conditional edge logic."""
    if state.should_retrieve:
        return "retrieve"
    return "generate"

def build_chat_graph(
    llm,
    retriever,
    db_session_factory,
    max_messages: int = 30,
    checkpointer = None,
):
    """Build the chat StateGraph with semantic routing and hybrid search."""
    
    # Create nodes
    prepare_context = create_prepare_context_node(db_session_factory, max_messages)
    route = create_route_node(llm)
    retrieve = create_retrieve_node(retriever, db_session_factory)
    generate = create_generate_node(llm, db_session_factory)
    update_memory = create_update_memory_node(llm, db_session_factory)
    
    # Build graph
    builder = StateGraph(ChatState)
    
    # Add nodes
    builder.add_node("prepare_context", prepare_context)
    builder.add_node("route", route)
    builder.add_node("retrieve", retrieve)
    builder.add_node("generate", generate)
    builder.add_node("update_memory", update_memory)
    
    # Add edges
    builder.add_edge(START, "prepare_context")
    builder.add_edge("prepare_context", "route")
    
    # Conditional routing
    builder.add_conditional_edges(
        "route",
        condition_routing,
        {
            "retrieve": "retrieve",
            "generate": "generate"
        }
    )
    
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", "update_memory")
    builder.add_edge("update_memory", END)
    
    return builder.compile(checkpointer=checkpointer)



def invoke_chat(
    graph,
    conversation_id: str,
    user_message: str,
) -> str:
    """Invoke the chat graph and return the response.
    
    Args:
        graph: Compiled chat graph
        conversation_id: UUID of the conversation
        user_message: User's message
    
    Returns:
        Assistant's response text
    """
    # When using checkpointer, we need to provide a thread_id in config
    config = {"configurable": {"thread_id": conversation_id}}
    
    result = graph.invoke(
        ChatState(
            conversation_id=conversation_id,
            user_message=user_message,
        ),
        config=config,
    )
    
    return result["response"]

