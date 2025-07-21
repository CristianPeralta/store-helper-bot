from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message as MessageModel
from app.models.chat import Chat as ChatModel
from app.repositories.message import message_repo
from app.schemas.message import Message, MessageCreate, MessageUpdate, MessageSender
from app.services.base import BaseService
from app.services.chat import chat_service


class MessageService(BaseService[MessageModel, MessageCreate, MessageUpdate]):
    """Message service with business logic for message operations."""
    
    async def get_multi_by_chat(
        self, 
        db: AsyncSession, 
        *, 
        chat_id: int,
        skip: int = 0, 
        limit: int = 100,
        current_user_id: Optional[int] = None
    ) -> List[MessageModel]:
        """Get messages for a specific chat with optional access control."""
        # Verify chat exists and user has access if current_user_id is provided
        if current_user_id is not None:
            chat = await chat_service.get(db, id=chat_id)
            if not chat or chat.user_id != current_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions to access these messages",
                )
        
        return await message_repo.get_multi_by_chat(
            db=db,
            chat_id=chat_id,
            skip=skip,
            limit=limit
        )
    
    async def create_with_owner(
        self, 
        db: AsyncSession, 
        *, 
        obj_in: MessageCreate, 
        owner_id: int,
        check_permissions: bool = True
    ) -> MessageModel:
        """Create a new message with an owner and optional permission check."""
        if check_permissions:
            # Verify chat exists and user has access
            chat = await chat_service.get(db, id=obj_in.chat_id)
            if not chat or chat.user_id != owner_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions to add messages to this chat",
                )
        
        # Add any business logic for message creation here
        # For example, you might want to:
        # - Check message rate limiting
        # - Process message content (e.g., markdown, sanitization)
        # - Trigger notifications
        
        return await message_repo.create_with_owner(
            db=db,
            obj_in=obj_in,
            owner_id=owner_id
        )
    
    async def get_last_bot_message(
        self,
        db: AsyncSession,
        *,
        chat_id: int,
        current_user_id: Optional[int] = None
    ) -> Optional[MessageModel]:
        """Get the last bot message in a chat with optional access control."""
        if current_user_id is not None:
            chat = await chat_service.get(db, id=chat_id)
            if not chat or chat.user_id != current_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions to access this chat",
                )
        
        return await message_repo.get_last_bot_message(db, chat_id=chat_id)
    
    async def update(
        self, 
        db: AsyncSession, 
        *, 
        id: int, 
        obj_in: MessageUpdate,
        owner_id: Optional[int] = None
    ) -> Optional[MessageModel]:
        """Update a message with optional ownership check."""
        message = await message_repo.get(db, id=id)
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found",
            )
        
        # Check ownership if owner_id is provided
        if owner_id is not None and message.owner_id != owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to update this message",
            )
        
        # Add any business logic for message updates here
        # For example, you might want to:
        # - Prevent editing messages after a certain time
        # - Log message edits
        # - Validate the new content
        
        return await message_repo.update(db, db_obj=message, obj_in=obj_in)


# Create a singleton instance
message_service = MessageService(message_repo)
