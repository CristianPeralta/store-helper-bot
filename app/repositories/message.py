from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.message import Message as MessageModel
from app.db.repositories.base import BaseRepository
from app.schemas.message import MessageCreate, MessageUpdate, MessageSender


class MessageRepository(BaseRepository[MessageModel, MessageCreate, MessageUpdate]):
    """Message repository with custom methods for message operations."""
    
    async def get_multi_by_chat(
        self, 
        db: AsyncSession, 
        *, 
        chat_id: int,
        skip: int = 0, 
        limit: int = 100
    ) -> List[MessageModel]:
        """Get multiple messages for a specific chat with pagination."""
        result = await db.execute(
            select(self.model)
            .where(self.model.chat_id == chat_id)
            .order_by(self.model.created_at.asc())  # Oldest first
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def create_with_owner(
        self, 
        db: AsyncSession, 
        *, 
        obj_in: MessageCreate, 
        owner_id: int
    ) -> MessageModel:
        """Create a new message with an owner."""
        db_obj = self.model(
            **obj_in.dict(),
            owner_id=owner_id
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def get_last_bot_message(
        self,
        db: AsyncSession,
        *,
        chat_id: int
    ) -> Optional[MessageModel]:
        """Get the last bot message in a chat."""
        result = await db.execute(
            select(self.model)
            .where(
                (self.model.chat_id == chat_id) &
                (self.model.sender == MessageSender.BOT)
            )
            .order_by(self.model.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()


# Create a singleton instance
message_repo = MessageRepository(MessageModel)
