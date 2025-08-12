from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas import BaseSchema, ResponseSchema


class SenderEnum(str, Enum):
    """Enum for message senders."""
    CLIENT = "CLIENT"
    BOT = "BOT"


class IntentEnum(str, Enum):
    """Enum for message intents."""
    GENERAL_QUESTION = "GENERAL_QUESTION"
    GREETING = "GREETING"
    STORE_INFO = "STORE_INFO"
    STORE_HOURS = "STORE_HOURS"
    STORE_CONTACT = "STORE_CONTACT"
    STORE_PROMOTIONS = "STORE_PROMOTIONS"
    STORE_PAYMENT_METHODS = "STORE_PAYMENT_METHODS"
    STORE_SOCIAL_MEDIA = "STORE_SOCIAL_MEDIA"
    STORE_LOCATION = "STORE_LOCATION"
    PRODUCT_LIST = "PRODUCT_LIST"
    PRODUCT_CATEGORIES = "PRODUCT_CATEGORIES"
    PRODUCT_DETAILS = "PRODUCT_DETAILS"
    PRODUCT_LIST_BY_CATEGORY = "PRODUCT_LIST_BY_CATEGORY"
    HUMAN_ASSISTANCE = "HUMAN_ASSISTANCE"
    OTHER = "OTHER"


# Shared properties
class MessageBase(BaseSchema):
    """Base schema for Message with common fields."""
    content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The message content"
    )
    intent: Optional[IntentEnum] = Field(
        None,
        description="The intent of the message"
    )
    sender: SenderEnum = Field(
        ...,
        description="The sender of the message (client or bot)"
    )


# Properties to receive on message creation
class MessageCreate(MessageBase):
    """Schema for creating a new message."""
    chat_id: str = Field(
        ...,
        description="ID of the chat this message belongs to"
    )


# Properties to receive on message update
class MessageUpdate(BaseSchema):
    """Schema for updating an existing message."""
    content: Optional[str] = Field(
        None,
        min_length=1,
        max_length=2000,
        description="The updated message content"
    )
    intent: Optional[IntentEnum] = Field(
        None,
        description="Updated intent of the message"
    )


# Properties shared by models stored in DB
class MessageInDBBase(MessageBase):
    """Base schema for message data stored in the database."""
    id: str
    chat_id: str
    created_at: datetime
    intent: Optional[IntentEnum] = Field(
        None,
        description="Intent of the message"
    )
    class Config:
        from_attributes = True


# Properties to return to client
class MessageResponse(MessageInDBBase, ResponseSchema):
    """Schema for message data returned to the client."""
    pass


# Properties stored in DB
class MessageInDB(MessageInDBBase):
    """Schema for message data stored in the database."""
    pass


# Additional response models
class MessageListResponse(ResponseSchema):
    """Schema for paginated list of messages."""
    data: list[MessageResponse] = Field(
        default_factory=list,
        description="List of messages"
    )
    total: int = Field(
        0,
        description="Total number of messages"
    )
    page: int = Field(
        1,
        description="Current page number"
    )
    page_size: int = Field(
        20,
        description="Number of items per page"
    )
    pages: int = Field(
        0,
        description="Total number of pages"
    )


class MessageCreateResponse(ResponseSchema):
    """Response schema for message creation."""
    data: MessageResponse = Field(
        ...,
        description="The created message"
    )


class MessageListQuery(BaseModel):
    """Query parameters for listing messages."""
    chat_id: Optional[str] = Field(
        None,
        description="Filter messages by chat ID"
    )
    sender: Optional[SenderEnum] = Field(
        None,
        description="Filter messages by sender"
    )
    intent: Optional[IntentEnum] = Field(
        None,
        description="Filter messages by intent"
    )
    start_date: Optional[datetime] = Field(
        None,
        description="Filter messages created after this date"
    )
    end_date: Optional[datetime] = Field(
        None,
        description="Filter messages created before this date"
    )
    sort_by: Optional[str] = Field(
        "created_at",
        description="Field to sort by (e.g., 'created_at', 'id')"
    )
    sort_order: str = Field(
        "asc",
        description="Sort order: 'asc' for ascending, 'desc' for descending",
        pattern="^(asc|desc)$"
    )
    skip: int = Field(
        0,
        ge=0,
        description="Number of items to skip"
    )
    limit: int = Field(
        100,
        ge=1,
        le=100,
        description="Number of items to return"
    )
