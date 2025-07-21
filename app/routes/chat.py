from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict

from app.db.session import get_db
from app.schemas.chat import ChatResponse, ChatInDB
from app.services.chat import chat_service

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("/", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    chat_data: Dict[str, str] = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new chat session.
    
    - **client_name**: Optional name of the client (in request body)
    - **client_email**: Optional email of the client (in request body)
    """
    try:
        client_name = chat_data.get("client_name")
        client_email = chat_data.get("client_email")
        
        chat = await chat_service.create_chat(
            db,
            client_name=client_name,
            client_email=client_email
        )
        chat_response = ChatInDB.model_validate(chat, from_attributes=True)
        return chat_response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating chat: {str(e)}"
        )

@router.get("/", response_model=List[ChatResponse])
async def get_all_chats(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all chats.
    
    - **skip**: Optional number of records to skip
    - **limit**: Optional number of records to return
    """
    chats = await chat_service.get_active_chats(
        db,
        skip=skip,
        limit=limit
    )
    chat_responses = [ChatInDB.model_validate(chat, from_attributes=True) for chat in chats]
    return chat_responses

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
    chat_response = ChatInDB.model_validate(chat, from_attributes=True)
    return chat_response