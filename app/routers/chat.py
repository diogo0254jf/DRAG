from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.models import Conversation, Message
from app.db.session import get_session
from app.schemas import ChatRequest, ChatResponse
from app.services.conversations import (
    get_conversation,
    parse_conversation_id,
)

router = APIRouter(tags=["chat"])


def _ensure_conversation(db: Session, conversation_id: str | None) -> Conversation:
    """Ensure conversation exists, create if needed."""
    if not conversation_id:
        conversation = Conversation()
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return conversation

    try:
        conv_uuid = parse_conversation_id(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid conversation_id") from exc

    conversation = get_conversation(db, conv_uuid)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    request: Request,
    db: Session = Depends(get_session),
) -> ChatResponse:
    """Chat endpoint using LangGraph StateGraph.
    
    This endpoint:
    1. Ensures conversation exists
    2. Saves user message to database
    3. Invokes chat graph for response generation
    4. Saves assistant response to database
    """
    # Ensure conversation exists
    conversation = _ensure_conversation(db, payload.conversation_id)

    # Save user message
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=payload.message,
    )
    db.add(user_message)
    db.commit()

    # Invoke chat graph
    try:
        from app.services.chat_graph import invoke_chat
        
        response_text = invoke_chat(
            request.app.state.chat_graph,
            str(conversation.id),
            payload.message,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Save assistant response
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=response_text,
    )
    db.add(assistant_message)
    db.commit()

    return ChatResponse(
        conversation_id=str(conversation.id),
        response=response_text,
    )

