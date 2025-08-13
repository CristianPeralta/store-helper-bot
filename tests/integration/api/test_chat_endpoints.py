"""Integration tests for chat API endpoints."""
import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat import Chat, Intent as ChatIntent
from app.db.models.message import Message, Sender, Intent as MessageIntent

pytestmark = pytest.mark.asyncio

class TestChatEndpoints:
    """Test cases for chat-related API endpoints."""
    
    async def test_create_chat(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test creating a new chat via API."""
        chat_data = {
            "client_name": "Test User",
            "client_email": "test@example.com",
        }
        
        # Don't use db_session.begin() here as the endpoint manages its own transaction
        response = await async_client.post("/api/chats/", json=chat_data)
        assert response.status_code == status.HTTP_201_CREATED
        
        data = response.json()
        assert "id" in data
        assert data["client_name"] == chat_data["client_name"]
        assert data["client_email"] == chat_data["client_email"]
        assert data["transferred_to_operator"] is False
        
        # Verify the chat was actually created in the database
        # Don't use a transaction here since the session is already in one
        result = await db_session.execute(
            text("SELECT * FROM chats WHERE id = :chat_id"), 
            {"chat_id": data["id"]}
        )
        db_chat = result.first()
        assert db_chat is not None, "Chat not found in database"
        assert db_chat.client_name == chat_data["client_name"], f"Expected client_name '{chat_data['client_name']}', got '{db_chat.client_name}'"
    
    async def test_get_chat_by_id(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test retrieving a chat by its ID."""
        # Create and commit test chat in its own transaction
        async with db_session.begin():
            chat = Chat(
                client_name="Test User",
                client_email="test@example.com",
                initial_intent=ChatIntent.GENERAL_QUESTION
            )
            db_session.add(chat)
            await db_session.flush()
            chat_id = str(chat.id)
        
        # Test retrieving the chat
        response = await async_client.get(f"/api/chats/{chat_id}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["id"] == chat_id
        assert data["client_name"] == "Test User"
        assert data["client_email"] == "test@example.com"
        assert data["initial_intent"] == "GENERAL_QUESTION"
    
    async def test_get_chat_not_found(self, async_client: AsyncClient):
        """Test retrieving a non-existent chat returns 404."""
        # No need for db_session here as we're just testing a 404
        response = await async_client.get("/api/chats/00000000-0000-0000-0000-000000000000")
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    async def test_get_chat_messages(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test retrieving messages for a chat."""
        # Create a chat with messages in a transaction
        async with db_session.begin():
            chat = Chat(
                client_name="Test User",
                client_email="test@example.com",
                initial_intent=ChatIntent.GENERAL_QUESTION
            )
            db_session.add(chat)
            await db_session.flush()
            chat_id = str(chat.id)
            
            # Create messages for the chat
            messages = [
                Message(
                    id=f"msg_{i}",  # Explicit ID for deterministic ordering
                    chat_id=chat.id,
                    content=f"Message {i}",
                    sender=Sender.CLIENT if i % 2 == 0 else Sender.BOT,
                    intent=MessageIntent.GREETING if i == 0 else MessageIntent.GENERAL_QUESTION
                ) for i in range(3)
            ]
            db_session.add_all(messages)
            await db_session.flush()
        
        # Test retrieving the messages
        response = await async_client.get(f"/api/chats/{chat_id}/messages")
        assert response.status_code == status.HTTP_200_OK
        
        # The response should be a dictionary with a 'messages' key containing the list
        data = response.json()
        assert isinstance(data, dict)
        assert "messages" in data
        assert isinstance(data["messages"], list)
        assert len(data["messages"]) == 3
        
        # Sort messages by content to ensure consistent ordering
        messages_sorted = sorted(data["messages"], key=lambda x: x["content"])
        for i, message in enumerate(messages_sorted):
            assert message["chat_id"] == chat_id
            assert message["content"] == f"Message {i}"
    
    async def test_get_chat_messages_empty(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test retrieving messages for a chat with no messages."""
        # Create a chat with no messages in a transaction
        async with db_session.begin():
            chat = Chat(
                client_name="Test User",
                client_email="test@example.com",
                initial_intent=ChatIntent.GENERAL_QUESTION
            )
            db_session.add(chat)
            await db_session.flush()
            chat_id = str(chat.id)
        
        # Test retrieving messages for the chat
        response = await async_client.get(f"/api/chats/{chat_id}/messages")
        assert response.status_code == status.HTTP_200_OK
        
        # The response should be a dictionary with an empty 'messages' list
        data = response.json()
        assert isinstance(data, dict)
        assert "messages" in data
        assert data["messages"] == []
        
    async def test_get_all_chats(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test retrieving all chats with pagination."""
        # Create test chats in a transaction
        async with db_session.begin():
            chats = [
                Chat(
                    id=f"chat_{i}",  # Explicit ID for deterministic ordering
                    client_name=f"User {i}",
                    client_email=f"user{i}@example.com",
                    initial_intent=ChatIntent.GENERAL_QUESTION
                ) for i in range(5)
            ]
            db_session.add_all(chats)
            await db_session.flush()
        
        # Test pagination with default parameters
        response = await async_client.get("/api/chats/")
        assert response.status_code == status.HTTP_200_OK
        
        # The response should be a dict with pagination info and data list
        data = response.json()
        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        assert "data" in data, "Response missing 'data' key"
        assert isinstance(data["data"], list), f"Expected data to be a list, got {type(data['data'])}"
        assert len(data["data"]) == 5, f"Expected 5 chats, got {len(data['data'])}"
        
        # Test with explicit pagination parameters
        response = await async_client.get("/api/chats/?skip=0&limit=2")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        assert "data" in data, "Response missing 'data' key"
        assert isinstance(data["data"], list), f"Expected data to be a list, got {type(data['data'])}"
        assert len(data["data"]) == 2, f"Expected 2 chats, got {len(data['data'])}"
        
        # Test second page
        response = await async_client.get("/api/chats/?skip=2&limit=2")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        assert "data" in data, "Response missing 'data' key"
        assert isinstance(data["data"], list), f"Expected data to be a list, got {type(data['data'])}"
        assert len(data["data"]) == 2, f"Expected 2 more chats, got {len(data['data'])}"
        
        # Test third page (last item)
        response = await async_client.get("/api/chats/?skip=4&limit=2")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        assert "data" in data, "Response missing 'data' key"
        assert isinstance(data["data"], list), f"Expected data to be a list, got {type(data['data'])}"
        assert len(data["data"]) == 1, f"Expected last chat, got {len(data['data'])} chats"
        
        # Test page beyond available data
        response = await async_client.get("/api/chats/?skip=10&limit=2")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, dict), f"Expected dict, got {type(data)}"
        assert "data" in data, "Response missing 'data' key"
        assert isinstance(data["data"], list), f"Expected data to be a list, got {type(data['data'])}"
        assert len(data["data"]) == 0, f"Expected no chats, got {len(data['data'])}"
