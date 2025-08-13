from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.message import MessageResponse, MessageListQuery
from app.services.message import message_service

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
