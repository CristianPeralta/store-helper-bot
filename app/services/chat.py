from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat import Chat as ChatModel
from app.schemas.chat import ChatCreate, ChatUpdate
from . import BaseService


class ChatService(BaseService[ChatModel, ChatCreate, ChatUpdate]):
    """Service for managing chats and related operations."""

    # Lets define a service that will save client_name, client_email, transferred_to_operator, operator_transfer_time
    async def transfer_to_operator(
        self, db: AsyncSession, *, chat_id: str, client_name: str, client_email: str, query: Optional[str] = None, inquiry_id: Optional[str] = None
    ) -> Optional[ChatModel]:
        """Save client information for transfer."""
        chat = await self.get(db, id=chat_id)
        if not chat:
            return None
        chat.client_name = client_name
        chat.client_email = client_email
        chat.transferred_to_operator = True
        chat.operator_transfer_time = datetime.now(timezone.utc).replace(tzinfo=None)
        chat.transfer_inquiry_id = inquiry_id
        chat.transfer_query = query
        db.add(chat)
        await db.commit()
        await db.refresh(chat)
        return chat

# Create a singleton instance
chat_service = ChatService(ChatModel)
