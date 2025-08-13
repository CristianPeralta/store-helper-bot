"""Integration tests for message API endpoints."""
import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat import Chat, Intent as ChatIntent
from app.db.models.message import Message, Sender, Intent as MessageIntent

pytestmark = pytest.mark.asyncio

class TestMessageEndpoints:
    """Test cases for message-related API endpoints."""
    
    async def test_get_messages_filtered(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test retrieving messages with filtering by chat_id."""
        # Create test chats and messages
        chat1 = Chat(
            client_name="User 1",
            client_email="user1@example.com",
            initial_intent=ChatIntent.GENERAL_QUESTION
        )
        chat2 = Chat(
            client_name="User 2",
            client_email="user2@example.com",
            initial_intent=ChatIntent.GENERAL_QUESTION
        )
        db_session.add_all([chat1, chat2])
        await db_session.flush()
        
        # Create messages for both chats
        messages = [
            Message(chat_id=chat1.id, content="Hello 1", sender=Sender.CLIENT, intent=MessageIntent.GREETING),
            Message(chat_id=chat1.id, content="Hi there!", sender=Sender.BOT, intent=MessageIntent.GREETING),
            Message(chat_id=chat2.id, content="Another chat", sender=Sender.CLIENT, intent=MessageIntent.GREETING),
        ]
        db_session.add_all(messages)
        await db_session.commit()
        
        # Clear the session to avoid transaction issues
        await db_session.close()
        
        # Store the chat IDs for later use
        chat1_id = str(chat1.id)
        chat2_id = str(chat2.id)
        
        # Test filtering by chat_id
        async with db_session.begin():
            response = await async_client.get(f"/api/messages/?chat_id={chat1_id}")
            assert response.status_code == status.HTTP_200_OK
            
            data = response.json()
            assert isinstance(data, list)  # The endpoint returns a list of messages directly
            assert len(data) == 2  # Should only get messages for chat1
            for msg in data:
                assert msg["chat_id"] == chat1_id
    
    async def test_get_messages_sorted(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test retrieving messages with sorting."""
        chat = Chat(
            client_name="Test User",
            client_email="test@example.com",
            initial_intent=ChatIntent.GENERAL_QUESTION
        )
        db_session.add(chat)
        await db_session.flush()
        
        # Create a test chat
        async with db_session.begin():
            chat = Chat(
                client_name="Test User",
                client_email="test@example.com",
                initial_intent=ChatIntent.GENERAL_QUESTION
            )
            db_session.add(chat)
            await db_session.flush()
            chat_id = chat.id
            
            # Create messages with different timestamps
            messages = [
                Message(chat_id=chat_id, content="First", sender=Sender.CLIENT, intent=MessageIntent.GREETING),
                Message(chat_id=chat_id, content="Second", sender=Sender.BOT, intent=MessageIntent.GREETING),
                Message(chat_id=chat_id, content="Third", sender=Sender.CLIENT, intent=MessageIntent.GREETING),
            ]
            db_session.add_all(messages)
            await db_session.commit()
        
        # Test ascending order
        async with db_session.begin():
            response = await async_client.get(f"/api/messages/?chat_id={chat_id}&sort_order=asc")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 3
            # Messages should be in ascending order by created_at
            contents = [msg["content"] for msg in data]
            assert sorted(contents) == contents
        
        # Test descending order
        async with db_session.begin():
            response = await async_client.get(f"/api/messages/?chat_id={chat_id}&sort_order=desc")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 3
            # Messages should be in descending order by created_at
            contents = [msg["content"] for msg in data]
            assert sorted(contents, reverse=True) == contents
    
    async def test_get_messages_pagination(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test message retrieval with pagination."""
        chat = Chat(
            client_name="Test User",
            client_email="test@example.com",
            initial_intent=ChatIntent.GENERAL_QUESTION
        )
        db_session.add(chat)
        await db_session.flush()
        
        # Create a test chat
        async with db_session.begin():
            chat = Chat(
                client_name="Test User",
                client_email="test@example.com",
                initial_intent=ChatIntent.GENERAL_QUESTION
            )
            db_session.add(chat)
            await db_session.flush()
            chat_id = chat.id
            
            # Create multiple messages
            messages = [
                Message(
                    chat_id=chat_id, 
                    content=f"Message {i}", 
                    sender=Sender.CLIENT if i % 2 == 0 else Sender.BOT,
                    intent=MessageIntent.GREETING
                )
                for i in range(15)
            ]
            db_session.add_all(messages)
            await db_session.commit()
        
        # Test first page
        async with db_session.begin():
            response = await async_client.get(f"/api/messages/?chat_id={chat_id}&limit=5&skip=0")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 5
        
        # Test second page
        async with db_session.begin():
            response = await async_client.get(f"/api/messages/?chat_id={chat_id}&limit=5&skip=5")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 5
        
        # Test third page (partial)
        async with db_session.begin():
            response = await async_client.get(f"/api/messages/?chat_id={chat_id}&limit=5&skip=10")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 5 
    
    async def test_get_messages_empty(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test retrieving messages when none exist."""
        async with db_session.begin():
            # Create a test chat to get a valid chat_id
            chat = Chat(
                client_name="Test User",
                client_email="test@example.com",
                initial_intent=ChatIntent.GENERAL_QUESTION
            )
            db_session.add(chat)
            await db_session.flush()
            chat_id = str(chat.id)
            
            response = await async_client.get(f"/api/messages/?chat_id={chat_id}")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 0
    
    async def test_get_messages_invalid_sort_field(self, async_client: AsyncClient):
        """Test that invalid sort fields return a validation error."""
        response = await async_client.get("/api/messages/?sort_by=invalid_field")
        # Should return 422 Unprocessable Entity for invalid sort field
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
