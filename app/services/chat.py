from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.chat import Chat as ChatModel
from app.db.models.message import Message as MessageModel, Sender, Intent
from app.schemas.chat import ChatCreate, ChatUpdate, ChatTransferRequest
from . import BaseService


class ChatService(BaseService[ChatModel, ChatCreate, ChatUpdate]):
    """Service for managing chats and related operations."""

    async def get_with_messages(
        self, db: AsyncSession, chat_id: UUID
    ) -> Optional[ChatModel]:
        """Get a chat with its messages."""
        result = await db.execute(
            select(self.model)
            .options(selectinload(self.model.messages))
            .where(self.model.id == str(chat_id))
        )
        return result.scalars().first()

    async def add_message(
        self,
        db: AsyncSession,
        *,
        chat_id: UUID,
        content: str,
        sender: Sender,
        intent: Intent = None
    ) -> MessageModel:
        """Add a message to a chat."""
        message = MessageModel(
            chat_id=chat_id,
            content=content,
            sender=sender,
            intent=intent
        )
        
        # Update chat's updated_at timestamp
        chat = await self.get(db, id=chat_id)
        if chat:
            chat.updated_at = datetime.utcnow()
            db.add(chat)
        
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message
    
    async def transfer_to_operator(
        self, db: AsyncSession, *, chat_id: UUID, transfer_data: ChatTransferRequest
    ) -> Optional[ChatModel]:
        """Transfer a chat to an operator."""
        chat = await self.get(db, id=chat_id)
        if not chat:
            return None

        chat.transferred_to_operator = True
        chat.operator_transfer_time = datetime.utcnow()
        
        # Add a system message about the transfer
        await self.add_message(
            db,
            chat_id=chat_id,
            content=f"Chat transferred to operator: {transfer_data.operator_email}",
            sender=Sender.BOT,
            intent=Intent.GENERAL_QUESTION
        )
        
        db.add(chat)
        await db.commit()
        await db.refresh(chat)
        return chat

    async def get_active_chats(
        self, db: AsyncSession, *, include_transferred: bool = False, skip: int = 0, limit: int = 100
    ) -> List[ChatModel]:
        """Get active chats, optionally including transferred ones."""
        query = select(self.model).where(
            self.model.transferred_to_operator == include_transferred
        )
        
        result = await db.execute(
            query.order_by(self.model.updated_at.desc())
                 .offset(skip)
                 .limit(limit)
                 .options(selectinload(self.model.messages))
        )
        return result.scalars().all()

    async def get_chat_messages(
        self, db: AsyncSession, chat_id: UUID, skip: int = 0, limit: int = 100,
        sort_by: str = "created_at"
    ) -> List[MessageModel]:
        """Get messages for a specific chat."""
        chat = await self.get_with_messages(db, chat_id)
        if not chat:
            return []
        
        # Sort messages by the specified field
        sorted_messages = sorted(chat.messages, key=lambda x: getattr(x, sort_by))
        return sorted_messages[skip:skip + limit]

    async def get_chat_by_client_email(
        self, db: AsyncSession, email: str, skip: int = 0, limit: int = 100
    ) -> List[ChatModel]:
        """Get chats by client email."""
        result = await db.execute(
            select(self.model)
            .where(self.model.client_email == email)
            .order_by(self.model.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .options(selectinload(self.model.messages))
        )
        return result.scalars().all()

    # Lets define a service that will save client_name, client_email, transferred_to_operator, operator_transfer_time
    async def save_client_info_for_transfer(
        self, db: AsyncSession, *, chat_id: str, client_name: str, client_email: str, query: Optional[str] = None, inquiry_id: Optional[str] = None
    ) -> Optional[ChatModel]:
        """Save client information for transfer."""
        chat = await self.get(db, id=chat_id)
        if not chat:
            return None
        print("INITIATIING SAVE_CLIENT_INFO_FOR_TRANSFER")
        chat.client_name = client_name
        chat.client_email = client_email
        chat.transferred_to_operator = True
        chat.operator_transfer_time = datetime.now(timezone.utc).replace(tzinfo=None)
        chat.transfer_inquiry_id = inquiry_id
        chat.transfer_query = query
        db.add(chat)
        await db.commit()
        await db.refresh(chat)
        print("SAVED CLIENT INFO FOR TRANSFER", chat)
        return chat

# Create a singleton instance
chat_service = ChatService(ChatModel)
