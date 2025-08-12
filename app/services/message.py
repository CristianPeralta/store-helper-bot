from datetime import datetime
from typing import List

from sqlalchemy import select, Column, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.message import Message as MessageModel
from app.db.models.chat import Chat as ChatModel
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
        """Get messages with filtering, sorting and pagination."""
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
        
        # Apply sorting
        sort_field: Column = getattr(self.model, query_params.sort_by, self.model.created_at)
        if query_params.sort_order.lower() == 'asc':
            query = query.order_by(sort_field.asc())
        else:
            query = query.order_by(sort_field.desc())
        
        # Apply pagination
        result = await db.execute(
            query.offset(query_params.skip)
                 .limit(query_params.limit)
        )
        
        return result.scalars().all()


    async def after_create(
        self, 
        db: AsyncSession, 
        db_obj: MessageModel, 
        obj_in: MessageCreate
    ) -> None:
        """Post-create hook to update the chat's updated_at timestamp."""
        await db.execute(
            update(ChatModel)
            .where(ChatModel.id == obj_in.chat_id)
            .values(updated_at=datetime.now())
        )
        await db.commit()

# Create a singleton instance
message_service = MessageService(MessageModel)
