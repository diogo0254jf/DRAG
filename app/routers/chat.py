import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.models import Conversation, Message
from app.db.session import get_session
from app.schemas import ChatRequest, ChatResponse
from app.services.conversations import (
    get_conversation,
    parse_conversation_id,
)

logger = logging.getLogger(__name__)

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


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    request: Request,
    db: Session = Depends(get_session),
):
    """Streaming chat endpoint using Server-Sent Events (SSE).

    Streams node-level updates as they happen in the LangGraph
    execution, then persists the final response.
    """
    conversation = _ensure_conversation(db, payload.conversation_id)

    # Save user message
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=payload.message,
    )
    db.add(user_msg)
    db.commit()

    conv_id = str(conversation.id)

    async def event_generator():
        from app.services.chat_graph import ChatState
        from app.db.session import SessionLocal

        graph = request.app.state.chat_graph
        config = {"configurable": {"thread_id": conv_id}}

        full_response = ""

        try:
            async for event in graph.astream(
                ChatState(
                    conversation_id=conv_id,
                    user_message=payload.message,
                ),
                config=config,
                stream_mode="updates",
            ):
                if "generate" in event:
                    response_text = event["generate"].get("response", "")
                    if response_text:
                        full_response = response_text
                        yield f"data: {json.dumps({'token': response_text, 'conversation_id': conv_id})}\n\n"

            # Persist the full response
            if full_response:
                save_db = SessionLocal()
                try:
                    save_db.add(
                        Message(
                            conversation_id=uuid.UUID(conv_id),
                            role="assistant",
                            content=full_response,
                        )
                    )
                    save_db.commit()
                finally:
                    save_db.close()

            yield f"data: {json.dumps({'done': True, 'conversation_id': conv_id})}\n\n"

        except Exception as exc:
            logger.error("Stream error: %s", exc)
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

