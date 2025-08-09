from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas import BaseSchema, ResponseSchema


class SenderEnum(str, Enum):
    """Enum for message senders."""
    CLIENT = "client"
    BOT = "bot"


class IntentEnum(str, Enum):
    """Enum for message intents."""
    GENERAL_QUESTION = "general_question"
    GREETING = "greeting"
    STORE_INFO = "store_info"
    STORE_HOURS = "store_hours"
    STORE_CONTACT = "store_contact"
    STORE_PROMOTIONS = "store_promotions"
    STORE_PAYMENT_METHODS = "store_payment_methods"
    STORE_SOCIAL_MEDIA = "store_social_media"
    STORE_LOCATION = "store_location"
    PRODUCT_LIST = "product_list"
    PRODUCT_CATEGORIES = "product_categories"
    PRODUCT_DETAILS = "product_details"
    PRODUCT_LIST_BY_CATEGORY = "product_list_by_category"
    HUMAN_ASSISTANCE = "human_assistance"
    OTHER = "other"


# Shared properties
class MessageBase(BaseSchema):
    """Base schema for Message with common fields."""
    content: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The message content"
    )
    sender: SenderEnum = Field(
        ...,
        description="The sender of the message (client or bot)"
    )


# Properties to receive on message creation
class MessageCreate(MessageBase):
    """Schema for creating a new message."""
    chat_id: UUID = Field(
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
    id: UUID
    chat_id: UUID
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
    chat_id: Optional[UUID] = Field(
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
    page: int = Field(
        1,
        ge=1,
        description="Page number for pagination"
    )
    page_size: int = Field(
        20,
        ge=1,
        le=100,
        description="Number of items per page"
    )
