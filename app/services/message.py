from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.message import Message as MessageModel, Sender, Intent
from app.schemas.message import MessageCreate, MessageUpdate, MessageListQuery
from . import BaseService


class MessageService(BaseService[MessageModel, MessageCreate, MessageUpdate]):
    """Service for managing messages and related operations."""

    async def get_messages(
        self,
        db: AsyncSession,
        *,
        query_params: MessageListQuery
    ) -> List[MessageModel]:
        """Get messages with filtering and pagination."""
        query = select(self.model)
        
        # Apply filters
        if query_params.chat_id:
            query = query.where(self.model.chat_id == query_params.chat_id)
            
        if query_params.sender:
            query = query.where(self.model.sender == query_params.sender)
            
        if query_params.intent:
            query = query.where(self.model.intent == query_params.intent)
            
        if query_params.start_date:
            query = query.where(self.model.created_at >= query_params.start_date)
            
        if query_params.end_date:
            query = query.where(self.model.created_at <= query_params.end_date)
        
        # Apply pagination
        result = await db.execute(
            query.order_by(self.model.created_at.desc())
                 .offset((query_params.page - 1) * query_params.page_size)
                 .limit(query_params.page_size)
        )
        
        return result.scalars().all()

    async def get_chat_messages(
        self,
        db: AsyncSession,
        chat_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[MessageModel]:
        """Get messages for a specific chat with pagination."""
        result = await db.execute(
            select(self.model)
            .where(self.model.chat_id == chat_id)
            .order_by(self.model.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_latest_message(
        self, db: AsyncSession, chat_id: UUID
    ) -> Optional[MessageModel]:
        """Get the most recent message in a chat."""
        result = await db.execute(
            select(self.model)
            .where(self.model.chat_id == chat_id)
            .order_by(self.model.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def create_message(
        self,
        db: AsyncSession,
        *,
        chat_id: UUID,
        content: str,
        sender: Sender,
        intent: Intent = None
    ) -> MessageModel:
        """Create a new message in a chat."""
        message = self.model(
            chat_id=chat_id,
            content=content,
            sender=sender,
            intent=intent
        )
        
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    async def update_message_intent(
        self,
        db: AsyncSession,
        *,
        message_id: UUID,
        new_intent: Intent
    ) -> Optional[MessageModel]:
        """Update the intent of a message."""
        message = await self.get(db, id=message_id)
        if not message:
            return None
            
        message.intent = new_intent
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message


# Create a singleton instance
message_service = MessageService(MessageModel)
