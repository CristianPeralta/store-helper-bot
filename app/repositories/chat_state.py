from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat_state import ChatState as ChatStateModel
from app.db.repositories.base import BaseRepository
from app.schemas.chat_state import ChatStateCreate, ChatStateUpdate


class ChatStateRepository(BaseRepository[ChatStateModel, ChatStateCreate, ChatStateUpdate]):
    """Chat state repository with custom methods for chat state operations."""
    
    async def get_by_chat_id(
        self, 
        db: AsyncSession, 
        *, 
        chat_id: int
    ) -> Optional[ChatStateModel]:
        """Get chat state by chat ID."""
        result = await db.execute(
            select(self.model)
            .where(self.model.chat_id == chat_id)
        )
        return result.scalars().first()
    
    async def get_or_create(
        self, 
        db: AsyncSession, 
        *, 
        chat_id: int,
        default_state: Optional[Dict[str, Any]] = None
    ) -> ChatStateModel:
        """Get chat state by chat ID, creating it with default state if it doesn't exist."""
        chat_state = await self.get_by_chat_id(db, chat_id=chat_id)
        if chat_state:
            return chat_state
            
        # Create default state if not provided
        if default_state is None:
            default_state = {
                "current_step": "initial",
                "data": {}
            }
            
        # Create new chat state
        obj_in = ChatStateCreate(
            chat_id=chat_id,
            state=default_state
        )
        return await self.create(db, obj_in=obj_in)
    
    async def update_state(
        self,
        db: AsyncSession,
        *,
        chat_id: int,
        state_updates: Dict[str, Any],
        merge: bool = True
    ) -> Optional[ChatStateModel]:
        """Update chat state with new values."""
        chat_state = await self.get_by_chat_id(db, chat_id=chat_id)
        if not chat_state:
            return None
            
        # Get current state
        current_state = chat_state.state.copy()
        
        # Update state
        if merge:
            updated_state = {**current_state, **state_updates}
        else:
            updated_state = state_updates
            
        # Update the chat state
        return await self.update(
            db,
            db_obj=chat_state,
            obj_in={"state": updated_state}
        )


# Create a singleton instance
chat_state_repo = ChatStateRepository(ChatStateModel)
