from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import Field, field_validator

from . import BaseSchema
from .chat import Chat

class MessageSender(str, Enum):
    """Enum for message sender types."""
    USER = "user"
    BOT = "bot"

class MessageBase(BaseSchema):
    """Base schema for Message with common fields."""
    content: str = Field(
        ...,
        title="Message Content",
        description="The text content of the message",
        min_length=1,
        max_length=4000,
        example="Hello, how can I help you today?"
    )
    sender: MessageSender = Field(
        ...,
        title="Message Sender",
        description="The sender of the message (user or bot)",
        example="bot"
    )
    chat_id: Optional[int] = Field(
        None,
        title="Chat ID",
        description="ID of the chat this message belongs to",
        example=1
    )

class MessageCreate(MessageBase):
    """Schema for creating a new message."""
    chat_id: int = Field(
        ...,
        title="Chat ID",
        description="ID of the chat this message belongs to",
        example=1
    )
    
    @field_validator('content')
    def content_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty")
        return v.strip()

class MessageUpdate(MessageBase):
    """Schema for updating an existing message."""
    content: str = Field(
        ...,
        title="Message Content",
        description="The updated text content of the message",
        min_length=1,
        max_length=4000,
        example="Hello, how can I help you today? (edited)"
    )
    sender: Optional[MessageSender] = None
    chat_id: Optional[int] = None

class MessageInDBBase(MessageBase):
    """Base schema for message data stored in the database."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
        use_enum_values = True

class Message(MessageInDBBase):
    """Schema for message data returned by the API."""
    chat: Optional[Chat] = None

class MessageInDB(MessageInDBBase):
    """Schema for message data stored in the database."""
    pass
