from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.schemas.chat import ChatResponse
from app.services.chat import chat_service

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("/", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    client_name: Optional[str] = None,
    client_email: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new chat session.
    
    - **client_name**: Optional name of the client
    - **client_email**: Optional email of the client
    """
    try:
        chat = await chat_service.create_chat(
            db,
            client_name=client_name,
            client_email=client_email
        )
        return {
            "success": True,
            "message": "Chat created successfully",
            **jsonable_encoder(chat)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating chat: {str(e)}"
        )

@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat(
    chat_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get chat details by ID.
    
    - **chat_id**: UUID of the chat to retrieve
    """
    chat = await chat_service.get_with_messages(db, chat_id=chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    return {
        "success": True,
        **jsonable_encoder(chat)
    }