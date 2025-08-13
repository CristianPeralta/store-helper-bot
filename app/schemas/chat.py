from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict

from app.schemas import BaseSchema, ResponseSchema
from app.schemas.message import MessageResponse


class IntentEnum(str, Enum):
    """Enum for chat intents."""
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
class ChatBase(BaseSchema):
    """Base schema for Chat with common fields."""
    client_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Name of the client if provided"
    )
    client_email: Optional[str] = Field(
        None,
        max_length=255,
        description="Email of the client if provided"
    )

    @field_validator('client_email')
    def validate_email(cls, v):
        if v is not None and "@" not in v:
            raise ValueError("Invalid email format")
        return v


# Properties to receive on chat creation
class ChatCreate(ChatBase):
    """Schema for creating a new chat."""
    pass


# Properties to receive on chat update
class ChatUpdate(ChatBase):
    """Schema for updating an existing chat."""
    transferred_to_operator: Optional[bool] = Field(
        None,
        description="Whether the chat has been transferred to an operator"
    )


# Properties shared by models stored in DB
class ChatInDBBase(ChatBase):
    """Base schema for chat data stored in the database."""
    id: str
    initial_intent: Optional[IntentEnum] = None
    transfer_inquiry_id: Optional[str] = None
    transfer_query: Optional[str] = None
    transferred_to_operator: bool = False
    operator_transfer_time: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "chat_123",
                "client_name": "John Doe",
                "client_email": "john.doe@example.com",
                "initial_intent": "GREETING",
                "transferred_to_operator": False,
                "transfer_inquiry_id": "inquiry_123",
                "transfer_query": "What is the store's address?",
                "operator_transfer_time": "2023-01-01T00:00:00",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
            }
        }
    )


# Properties to return to client
class ChatResponse(ChatInDBBase, ResponseSchema):
    """Schema for chat data returned to the client."""
    pass

class ChatMessagesResponse(BaseModel):
    """Schema for chat messages returned to the client."""
    messages: List[MessageResponse] = Field(
        default_factory=list,
        description="List of messages"
    )

# Properties stored in DB
class ChatInDB(ChatInDBBase):
    """Schema for chat data stored in the database."""
    pass


# Additional response models
class ChatListResponse(ResponseSchema):
    """Schema for paginated list of chats."""
    total: int = Field(
        0,
        description="Total number of chats"
    )
    page: int = Field(
        1,
        description="Current page number"
    )
    page_size: int = Field(
        10,
        description="Number of items per page"
    )
    pages: int = Field(
        0,
        description="Total number of pages"
    )
    data: List[ChatResponse] = Field(
        default_factory=list,
        description="List of chats"
    )


class ChatTransferRequest(BaseModel):
    """Schema for chat transfer request."""
    operator_email: str = Field(
        ...,
        description="Email of the operator to transfer the chat to"
    )
    transfer_reason: Optional[str] = Field(
        None,
        description="Reason for transferring the chat"
    )

    @field_validator('operator_email')
    def validate_operator_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid operator email format")
        return v
