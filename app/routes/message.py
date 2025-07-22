from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from app.db.session import get_db
from app.schemas.message import (
    MessageResponse, 
    MessageCreate, 
    MessageUpdate, 
    MessageListQuery,
    MessageListResponse,
    SenderEnum,
    IntentEnum
)
from app.services.message import message_service

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    message_data: MessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new message in a chat.
    
    - **chat_id**: ID of the chat this message belongs to (required)
    - **content**: The message content (required)
    - **sender**: The sender of the message (client or bot) (required)
    - **intent**: Optional intent of the message
    """
    try:
        message = await message_service.create(db, obj_in=message_data)
        return MessageResponse.model_validate(message, from_attributes=True)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating message: {str(e)}"
        )


@router.get("/", response_model=MessageListResponse)
async def list_messages(
    chat_id: Optional[UUID] = Query(None, description="Filter by chat ID"),
    sender: Optional[SenderEnum] = Query(None, description="Filter by sender (client or bot)"),
    intent: Optional[IntentEnum] = Query(None, description="Filter by intent"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a list of messages with filtering and pagination.
    
    - **chat_id**: Filter by chat ID
    - **sender**: Filter by sender (client or bot)
    - **intent**: Filter by intent
    - **start_date**: Filter messages created after this date
    - **end_date**: Filter messages created before this date
    - **page**: Page number for pagination
    - **page_size**: Number of items per page (max 100)
    """
    try:
        query_params = MessageListQuery(
            chat_id=chat_id,
            sender=sender,
            intent=intent,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size
        )
        
        messages = await message_service.get_messages(db, query_params=query_params)
        total = await message_service.count(db, **query_params.dict(exclude_none=True))
        
        return MessageListResponse(
            data=[MessageResponse.model_validate(msg, from_attributes=True) for msg in messages],
            total=total,
            page=page,
            page_size=page_size,
            pages=(total + page_size - 1) // page_size if page_size > 0 else 0
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving messages: {str(e)}"
        )


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a message by ID.
    
    - **message_id**: UUID of the message to retrieve
    """
    message = await message_service.get(db, id=message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    return MessageResponse.model_validate(message, from_attributes=True)


@router.patch("/{message_id}", response_model=MessageResponse)
async def update_message(
    message_id: UUID,
    message_update: MessageUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a message.
    
    - **message_id**: UUID of the message to update
    - **content**: Updated message content
    - **intent**: Updated intent
    """
    message = await message_service.get(db, id=message_id)
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    
    try:
        updated_message = await message_service.update(
            db,
            db_obj=message,
            obj_in=message_update
        )
        return MessageResponse.model_validate(updated_message, from_attributes=True)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating message: {str(e)}"
        )
