from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.chat import Chat
from app.db.models.message import Sender
from app.schemas.message import MessageResponse, MessageListQuery, MessageCreate, MessageCreateResponse
from app.services.message import message_service
from app.services.chat_processor import ChatProcessor

router = APIRouter(prefix="/messages", tags=["messages"])

@router.get("/", response_model=List[MessageResponse])
async def get_messages(
    chat_id: Optional[str] = Query(None, description="Filter by chat ID"),
    sort_by: Optional[str] = Query("created_at", description="Field to sort by (e.g., 'created_at', 'id')"),
    sort_order: str = Query("asc", description="Sort order: 'asc' or 'desc'", pattern="^(asc|desc)$"),
    skip: int = Query(0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get messages with filtering, sorting and pagination.
    
    - **chat_id**: Filter by chat ID (optional)
    - **sort_by**: Field to sort by (default: 'created_at')
    - **sort_order**: Sort order: 'asc' or 'desc' (default: 'desc')
    - **skip**: Number of items to skip (default: 0)
    - **limit**: Number of items to return (default: 100, max: 100)
    """
    query_params = MessageListQuery(
        chat_id=chat_id,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit
    )
    
    messages = await message_service.get_messages(
        db, 
        query_params=query_params,
    )
    return messages


@router.post("/", response_model=MessageCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    message: MessageCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new message and process it through the chat processor.
    
    - **message**: The message to create and process
    """
    try:
        # Check if chat exists
        chat = await db.get(Chat, message.chat_id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat with id {message.chat_id} not found"
            )
            
        # Check if message is empty
        if not message.content.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Message content cannot be empty"
            )

        # Create the user message
        message = await message_service.create(db, obj_in=message)
        
        # Initialize chat processor
        chat_processor = ChatProcessor(db)
        
        # Create initial state for the conversation
        state = {
            "messages": [],
            "chat_id": message.chat_id,
            "current_intent": None,
            "context": {}
        }
               
        # Commit the transaction
        await db.commit()
        await db.refresh(message)

        # Process the message through the chat processor in the background
        if message.sender == Sender.CLIENT:
            # Create a new session for the background task
            background_tasks.add_task(
                chat_processor.process_message,
                state,
                message
            )
        
        return MessageCreateResponse(
            data=message,
            message="Message processed successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        await db.rollback()
        raise
        
    except Exception as e:
        # Log the error and return a 500 response
        await db.rollback()
        print(f"Error creating message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )