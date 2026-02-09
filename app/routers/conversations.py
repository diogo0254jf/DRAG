from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Conversation, Message
from app.db.session import get_session
from app.schemas import CreateConversationResponse, MessageOut
from app.services.conversations import get_conversation, parse_conversation_id

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _require_conversation(db: Session, conversation_id: str) -> Conversation:
    try:
        conv_uuid = parse_conversation_id(conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid conversation_id") from exc

    conversation = get_conversation(db, conv_uuid)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.get("")
def list_conversations(db: Session = Depends(get_session)) -> list[dict]:
    """List all conversations with their last message preview."""
    conversations = (
        db.query(Conversation)
        .order_by(Conversation.created_at.desc())
        .limit(50)
        .all()
    )
    
    result = []
    for conv in conversations:
        last_msg = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .first()
        )
        result.append({
            "conversation_id": str(conv.id),
            "created_at": conv.created_at.isoformat(),
            "preview": last_msg.content[:50] + "..." if last_msg and len(last_msg.content) > 50 else (last_msg.content if last_msg else "Empty"),
            "message_count": db.query(Message).filter(Message.conversation_id == conv.id).count()
        })
    return result


@router.post("", response_model=CreateConversationResponse)
def create_conversation(db: Session = Depends(get_session)) -> CreateConversationResponse:
    conversation = Conversation()
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return CreateConversationResponse(conversation_id=str(conversation.id))


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(conversation_id: str, db: Session = Depends(get_session)) -> list[MessageOut]:
    conversation = _require_conversation(db, conversation_id)
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
        .all()
    )

    return [
        MessageOut(
            id=str(m.id),
            role=m.role,
            content=m.content,
            created_at=m.created_at,
        )
        for m in messages
    ]
