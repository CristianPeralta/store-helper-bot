from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat import Chat as ChatModel
from app.db.models.user import User as UserModel
from app.db.repositories.base import BaseRepository
from app.schemas.chat import ChatCreate, ChatUpdate


class ChatRepository(BaseRepository[ChatModel, ChatCreate, ChatUpdate]):
    """Chat repository with custom methods for chat operations."""
    
    async def get_multi_by_owner(
        self, 
        db: AsyncSession, 
        *, 
        owner_id: int,
        skip: int = 0, 
        limit: int = 100
    ) -> List[ChatModel]:
        """Get multiple chats by owner ID with pagination."""
        result = await db.execute(
            select(self.model)
            .where(self.model.user_id == owner_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def create_with_owner(
        self, 
        db: AsyncSession, 
        *, 
        obj_in: ChatCreate, 
        owner_id: int
    ) -> ChatModel:
        """Create a new chat with an owner."""
        db_obj = self.model(
            **obj_in.dict(),
            user_id=owner_id
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


# Create a singleton instance
chat_repo = ChatRepository(ChatModel)
