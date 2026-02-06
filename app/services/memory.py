from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.db.models import Conversation
from app.services.prompts import get_prompt


class MemoryPromptMissing(RuntimeError):
    pass


class MemoryUpdate(BaseModel):
    """Schema for structured memory update from LLM."""
    topic: str = Field(description="Main topic of the conversation")
    summary: str = Field(description="Brief summary of the conversation so far")


def build_memory_text(conversation: Conversation) -> str:
    """Build memory context text from conversation metadata."""
    parts = []
    if conversation.topic:
        parts.append(f"Topico: {conversation.topic}")
    if conversation.summary:
        parts.append(f"Resumo: {conversation.summary}")
    return "\n".join(parts)


def update_conversation_memory(
    db, 
    conversation: Conversation, 
    llm, 
    history: str,
) -> None:
    """Update conversation memory using structured output.
    
    Uses LLM with structured output to extract topic and summary,
    avoiding manual JSON parsing.
    """
    prompt = get_prompt(db, "memory_update")
    if not prompt:
        raise MemoryPromptMissing("Prompt 'memory_update' not configured")

    # Build prompt with current context
    rendered = prompt.template.format(
        history=history,
        summary=conversation.summary or "",
        topic=conversation.topic or "",
    )

    try:
        # Use structured output instead of manual JSON parsing
        structured_llm = llm.with_structured_output(MemoryUpdate)
        result: Optional[MemoryUpdate] = structured_llm.invoke(rendered)
        
        if result:
            if result.topic.strip():
                conversation.topic = result.topic.strip()
            if result.summary.strip():
                conversation.summary = result.summary.strip()
            
            conversation.memory_updated_at = datetime.utcnow()
            db.commit()
    except Exception:
        # If structured output fails, silently skip update
        # This is better than crashing the entire request
        pass