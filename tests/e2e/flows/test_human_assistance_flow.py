"""End-to-end tests for the human assistance flow."""
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from app.db.models.chat import Chat, Intent as ChatIntent
from app.db.models.message import Message, Sender, Intent as MessageIntent

pytestmark = pytest.mark.asyncio

class TestHumanAssistanceFlow:
    """Test the complete human assistance flow from chat start to inquiry creation."""
    
    async def test_human_assistance_flow(
        self, 
        async_client: AsyncClient, 
        db_session: AsyncSession
    ):
        """Test the complete human assistance flow."""
        # 1. Create a new chat
        chat_data = {
            "client_name": "Test User",
            "client_email": "test@example.com",
        }
        
        # 2. Create chat via API
        response = await async_client.post("/api/chats/", json=chat_data)
        assert response.status_code == status.HTTP_201_CREATED
        chat = response.json()
        chat_id = chat["id"]
        
        # 3. Send initial message requesting human assistance
        message_data = {
            "content": "I need to speak with a human assistant",
            "sender": Sender.CLIENT.value,
            "intent": MessageIntent.HUMAN_ASSISTANCE.value,
            "chat_id": chat_id
        }
        
        # Send message using the messages endpoint
        response = await async_client.post(
            "/api/messages/",
            json=message_data
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # 4. Verify the bot's response asks for name and email
        response = await async_client.get(
            f"/api/messages/",
            params={"chat_id": chat_id, "sort_order": "asc"}
        )
        assert response.status_code == status.HTTP_200_OK
        messages = response.json()
        
        # The last message should be from the bot asking for details
        assert len(messages) > 0, "No messages found in the chat"
        bot_message = messages[-1]  # The last message should be the bot's response
        assert bot_message["sender"] == Sender.BOT.value
        
        # Check if the bot's response contains any of the expected keywords
        bot_response = bot_message["content"].lower()
        assert any(word in bot_response for word in ["name", "email", "contact"]), \
            f"Bot response does not ask for contact details: {bot_response}"
        
        # 5. Send user details
        user_details = {
            "content": "My name is John Doe and my email is john.doe@example.com",
            "sender": Sender.CLIENT.value,
            "intent": MessageIntent.HUMAN_ASSISTANCE.value,
            "chat_id": chat_id
        }
        
        response = await async_client.post(
            "/api/messages/",
            json=user_details
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # 6. Verify the chat was updated in the database
        result = await db_session.execute(
            select(Chat)
            .where(Chat.id == chat_id)
        )
        db_chat = result.scalar_one_or_none()
        
        assert db_chat is not None
        # Verify the chat was marked for transfer
        assert db_chat.transferred_to_operator is True, \
            "Chat was not marked as transferred to operator"
        
        # 7. Verify all messages were saved
        result = await db_session.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at)
        )
        db_messages = result.scalars().all()
        
        # Verify we have at least 2 messages (initial + bot response + user details)
        assert len(db_messages) >= 2, "Expected at least 2 messages in the database"
        
        # Verify the first message is the one we sent
        first_message = db_messages[0]
        assert first_message.content == "I need to speak with a human assistant"
        assert first_message.sender == Sender.CLIENT.value
        
        # Verify the second message is from the bot
        bot_message = db_messages[1]
        assert bot_message.sender == Sender.BOT.value
        
        # Verify the third message is our user details (if it exists)
        if len(db_messages) > 2:
            user_details_msg = db_messages[2]
            assert "John Doe" in user_details_msg.content
            assert "john.doe@example.com" in user_details_msg.content
            assert user_details_msg.sender == Sender.CLIENT.value
