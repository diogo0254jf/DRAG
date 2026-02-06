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


def create_retrieve_node(retriever):
    """Create the retrieve node with access to the retriever."""
    
    def retrieve(state: ChatState) -> dict:
        """Retrieve relevant documents for RAG."""
        if state.error:
            return {}
        
        context, _ = retrieve_context(retriever, state.user_message)
        return {"context": context or ""}
    
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


def build_chat_graph(llm, retriever, db_session_factory, max_messages: int = 30):
    """Build the chat StateGraph.
    
    Args:
        llm: LangChain LLM instance
        retriever: Document retriever
        db_session_factory: Factory function that returns a database session
        max_messages: Maximum number of messages to include in history
    
    Returns:
        Compiled StateGraph
    """
    # Create nodes with dependencies injected
    prepare_context = create_prepare_context_node(db_session_factory, max_messages)
    retrieve = create_retrieve_node(retriever)
    generate = create_generate_node(llm, db_session_factory)
    update_memory = create_update_memory_node(llm, db_session_factory)
    
    # Build graph
    builder = StateGraph(ChatState)
    
    # Add nodes
    builder.add_node("prepare_context", prepare_context)
    builder.add_node("retrieve", retrieve)
    builder.add_node("generate", generate)
    builder.add_node("update_memory", update_memory)
    
    # Add edges
    builder.add_edge(START, "prepare_context")
    builder.add_edge("prepare_context", "retrieve")
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", "update_memory")
    builder.add_edge("update_memory", END)
    
    return builder.compile()


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
    result = graph.invoke(
        ChatState(
            conversation_id=conversation_id,
            user_message=user_message,
        )
    )
    
    return result["response"]
