import uuid
from typing import Sequence

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.messages.utils import trim_messages, count_tokens_approximately

from app.db.models import Conversation, Message


def parse_conversation_id(value: str) -> uuid.UUID:
    return uuid.UUID(value)


def get_conversation(db, conversation_id: uuid.UUID) -> Conversation | None:
    return db.get(Conversation, conversation_id)


def db_messages_to_langchain(messages: list[Message]) -> list[BaseMessage]:
    """Convert database Message objects to LangChain message format."""
    result = []
    for msg in messages:
        if msg.role == "user":
            result.append(HumanMessage(content=msg.content))
        else:
            result.append(AIMessage(content=msg.content))
    return result


def get_recent_messages(
    db,
    conversation_id: uuid.UUID,
    max_messages: int = 30,
) -> list[Message]:
    """Get recent messages from database, ordered chronologically."""
    rows = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(max_messages)
        .all()
    )
    return list(reversed(rows))


def get_trimmed_messages(
    messages: list[Message],
    max_tokens: int = 2000,
) -> list[BaseMessage]:
    """Convert and trim messages to fit within token limit.
    
    Uses LangChain's trim_messages with approximate token counting.
    Keeps the most recent messages that fit within the limit.
    """
    langchain_messages = db_messages_to_langchain(messages)
    
    if not langchain_messages:
        return []
    
    return trim_messages(
        langchain_messages,
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=max_tokens,
        start_on="human",
        end_on=("human", "ai"),
        include_system=True,
    )


def format_history(messages: Sequence[BaseMessage]) -> str:
    """Format LangChain messages as text for prompt injection."""
    parts = []
    for message in messages:
        if isinstance(message, HumanMessage):
            role = "Usuario"
        else:
            role = "Assistente"
        parts.append(f"{role}: {message.content}")
    return "\n".join(parts)

