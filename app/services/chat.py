from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.chat import Chat as ChatModel
from app.db.models.message import Message as MessageModel, Sender, Intent
from app.schemas.chat import ChatCreate, ChatUpdate, ChatTransferRequest
from . import BaseService


class ChatService(BaseService[ChatModel, ChatCreate, ChatUpdate]):
    """Service for managing chats and related operations."""

    async def add_message(
        self,
        db: AsyncSession,
        *,
        chat_id: str,
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


    # Lets define a service that will save client_name, client_email, transferred_to_operator, operator_transfer_time
    async def transfer_to_operator(
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
