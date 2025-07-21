from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import Field

from . import BaseSchema
from .chat import Chat

class ChatStateBase(BaseSchema):
    """Base schema for ChatState with common fields."""
    state: Dict[str, Any] = Field(
        default_factory=dict,
        title="Chat State",
        description="JSON object containing the chat state data",
        example={"current_step": "greeting", "data": {}}
    )
    chat_id: Optional[int] = Field(
        None,
        title="Chat ID",
        description="ID of the chat this state belongs to",
        example=1
    )

class ChatStateCreate(ChatStateBase):
    """Schema for creating a new chat state."""
    chat_id: int = Field(
        ...,
        title="Chat ID",
        description="ID of the chat this state belongs to",
        example=1
    )

class ChatStateUpdate(ChatStateBase):
    """Schema for updating an existing chat state."""
    state: Dict[str, Any] = Field(
        ...,
        title="Chat State",
        description="JSON object containing the updated chat state data",
        example={"current_step": "processing", "data": {"name": "John"}}
    )

class ChatStateInDBBase(ChatStateBase):
    """Base schema for chat state data stored in the database."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class ChatState(ChatStateInDBBase):
    """Schema for chat state data returned by the API."""
    chat: Optional[Chat] = None

class ChatStateInDB(ChatStateInDBBase):
    """Schema for chat state data stored in the database."""
    pass
