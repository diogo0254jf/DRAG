from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateConversationResponse(BaseModel):
    conversation_id: str


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    conversation_id: str
    response: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


class PromptOut(BaseModel):
    key: str
    template: str
    required_placeholders: list[str]
    updated_at: datetime


class PromptUpdate(BaseModel):
    template: Optional[str] = Field(default=None, min_length=1)
    required_placeholders: Optional[list[str]] = None


class PromptCreate(BaseModel):
    key: str = Field(min_length=1, max_length=64)
    template: str = Field(min_length=1)
    required_placeholders: Optional[list[str]] = None
