from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import Chat as ChatModel
from app.models.user import User as UserModel
from app.repositories.chat import chat_repo
from app.schemas.chat import Chat, ChatCreate, ChatUpdate
from app.services.base import BaseService


class ChatService(BaseService[ChatModel, ChatCreate, ChatUpdate]):
    """Chat service with business logic for chat operations."""
    
    async def get_multi_by_owner(
        self, 
        db: AsyncSession, 
        *, 
        owner_id: int,
        skip: int = 0, 
        limit: int = 100
    ) -> List[ChatModel]:
        """Get multiple chats owned by a specific user."""
        return await chat_repo.get_multi_by_owner(
            db=db,
            owner_id=owner_id,
            skip=skip,
            limit=limit
        )
    
    async def create_with_owner(
        self, 
        db: AsyncSession, 
        *, 
        obj_in: ChatCreate, 
        owner_id: int
    ) -> ChatModel:
        """Create a new chat for a specific owner."""
        # Here you could add business logic like:
        # - Check if user has reached max chats
        # - Validate chat creation rules
        # - Initialize chat state, etc.
        
        return await chat_repo.create_with_owner(
            db=db,
            obj_in=obj_in,
            owner_id=owner_id
        )
    
    async def update(
        self, 
        db: AsyncSession, 
        *, 
        id: int, 
        obj_in: ChatUpdate,
        owner_id: Optional[int] = None
    ) -> Optional[ChatModel]:
        """Update a chat with optional ownership check."""
        chat = await chat_repo.get(db, id=id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found",
            )
        
        # Check ownership if owner_id is provided
        if owner_id is not None and chat.user_id != owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        
        # Add any business logic for chat updates here
        
        return await chat_repo.update(db, db_obj=chat, obj_in=obj_in)
    
    async def remove(
        self, 
        db: AsyncSession, 
        *, 
        id: int, 
        owner_id: Optional[int] = None
    ) -> bool:
        """Delete a chat with optional ownership check."""
        chat = await chat_repo.get(db, id=id)
        if not chat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat not found",
            )
        
        # Check ownership if owner_id is provided
        if owner_id is not None and chat.user_id != owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        
        # Add any business logic before deletion here
        
        return await chat_repo.delete(db, id=id)


# Create a singleton instance
chat_service = ChatService(chat_repo)
