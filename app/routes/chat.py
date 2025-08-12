from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.chat import ChatResponse, ChatCreate, ChatListResponse, ChatMessagesResponse
from app.schemas.message import MessageListQuery
from app.services.chat import chat_service
from app.services.message import message_service

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("/", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    chat_data: ChatCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new chat session.
    
    - **client_name**: Optional name of the client (in request body)
    - **client_email**: Optional email of the client (in request body)
    """
    try:
        chat = await chat_service.create_chat(
            db,
            client_name=chat_data.client_name,
            client_email=chat_data.client_email
        )
        return ChatResponse.model_validate(chat, from_attributes=True)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating chat: {str(e)}"
        )

@router.get("/", response_model=ChatListResponse)
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
    chats = await chat_service.get_multi(
        db,
        skip=skip,
        limit=limit
    )
    chat_responses = [ChatResponse.model_validate(chat, from_attributes=True) for chat in chats]
    chat_list_response = ChatListResponse(
        total=len(chats),
        page=skip // limit + 1,
        page_size=limit,
        pages=(len(chats) + limit - 1) // limit,
        data=chat_responses,
    )
    return chat_list_response

@router.get("/{chat_id}/messages", response_model=ChatMessagesResponse)
async def get_chat_messages(
    chat_id: str,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get chat messages by ID.
    
    - **chat_id**: UUID of the chat to retrieve
    - **skip**: Optional number of records to skip
    - **limit**: Optional number of records to return
    """
    chat = await chat_service.get(db, id=chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    query_params = MessageListQuery(
        chat_id=chat_id,
        sort_by="created_at",
        sort_order="asc",
        skip=skip,
        limit=limit
    )
    messages = await message_service.get_messages(db, query_params=query_params)
    return ChatMessagesResponse.model_validate({"messages": messages}, from_attributes=True)

@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat_by_id(
    chat_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get chat by ID.
    
    - **chat_id**: UUID of the chat to retrieve
    """
    chat = await chat_service.get(db, id=chat_id)
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chat not found"
        )
    return ChatResponse.model_validate(chat, from_attributes=True)
