from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_state import ChatState as ChatStateModel
from app.models.chat import Chat as ChatModel
from app.repositories.chat_state import chat_state_repo
from app.schemas.chat_state import ChatState, ChatStateCreate, ChatStateUpdate
from app.services.base import BaseService
from app.services.chat import chat_service


class ChatStateService(BaseService[ChatStateModel, ChatStateCreate, ChatStateUpdate]):
    """Chat state service with business logic for chat state operations."""
    
    async def get_by_chat_id(
        self, 
        db: AsyncSession, 
        *, 
        chat_id: int,
        current_user_id: Optional[int] = None
    ) -> Optional[ChatStateModel]:
        """Get chat state by chat ID with optional access control."""
        if current_user_id is not None:
            # Verify chat exists and user has access
            chat = await chat_service.get(db, id=chat_id)
            if not chat or chat.user_id != current_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions to access this chat state",
                )
        
        return await chat_state_repo.get_by_chat_id(db, chat_id=chat_id)
    
    async def get_or_create(
        self, 
        db: AsyncSession, 
        *, 
        chat_id: int,
        current_user_id: Optional[int] = None,
        default_state: Optional[Dict[str, Any]] = None
    ) -> ChatStateModel:
        """Get or create chat state with optional access control and default state."""
        if current_user_id is not None:
            # Verify chat exists and user has access
            chat = await chat_service.get(db, id=chat_id)
            if not chat or chat.user_id != current_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions to access this chat state",
                )
        
        return await chat_state_repo.get_or_create(
            db,
            chat_id=chat_id,
            default_state=default_state
        )
    
    async def update_state(
        self,
        db: AsyncSession,
        *,
        chat_id: int,
        state_updates: Dict[str, Any],
        merge: bool = True,
        current_user_id: Optional[int] = None
    ) -> Optional[ChatStateModel]:
        """Update chat state with new values and optional access control."""
        if current_user_id is not None:
            # Verify chat exists and user has access
            chat = await chat_service.get(db, id=chat_id)
            if not chat or chat.user_id != current_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions to update this chat state",
                )
        
        # Add any business logic for state updates here
        # For example, you might want to:
        # - Validate state transitions
        # - Log state changes
        # - Trigger side effects based on state changes
        
        return await chat_state_repo.update_state(
            db,
            chat_id=chat_id,
            state_updates=state_updates,
            merge=merge
        )
    
    async def reset_state(
        self,
        db: AsyncSession,
        *,
        chat_id: int,
        current_user_id: Optional[int] = None
    ) -> ChatStateModel:
        """Reset chat state to initial values."""
        if current_user_id is not None:
            # Verify chat exists and user has access
            chat = await chat_service.get(db, id=chat_id)
            if not chat or chat.user_id != current_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions to reset this chat state",
                )
        
        # Define initial state
        initial_state = {
            "current_step": "initial",
            "data": {}
        }
        
        # Get or create chat state with initial state
        chat_state = await chat_state_repo.get_by_chat_id(db, chat_id=chat_id)
        if chat_state:
            # Update existing state
            return await chat_state_repo.update(
                db,
                db_obj=chat_state,
                obj_in={"state": initial_state}
            )
        else:
            # Create new state
            return await chat_state_repo.create(
                db,
                obj_in=ChatStateCreate(
                    chat_id=chat_id,
                    state=initial_state
                )
            )


# Create a singleton instance
chat_state_service = ChatStateService(chat_state_repo)
