from datetime import datetime
from typing import Optional, List
from pydantic import Field

from . import BaseSchema
from .user import User

class ChatBase(BaseSchema):
    """Base schema for Chat with common fields."""
    user_id: Optional[int] = Field(
        None,
        title="User ID",
        description="ID of the user who owns this chat",
        example=1
    )

class ChatCreate(ChatBase):
    """Schema for creating a new chat."""
    user_id: int = Field(
        ...,
        title="User ID",
        description="ID of the user who owns this chat",
        example=1
    )

class ChatUpdate(ChatBase):
    """Schema for updating an existing chat."""
    pass

class ChatInDBBase(ChatBase):
    """Base schema for chat data stored in the database."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class Chat(ChatInDBBase):
    """Schema for chat data returned by the API."""
    user: Optional[User] = None

class ChatInDB(ChatInDBBase):
    """Schema for chat data stored in the database."""
    pass

class ChatWithMessages(Chat):
    """Schema for chat data including its messages."""
    messages: List["Message"] = []

# Import here to avoid circular imports
from .message import Message  # noqa
ChatWithMessages.model_rebuild()
