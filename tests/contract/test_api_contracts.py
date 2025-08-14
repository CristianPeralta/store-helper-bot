"""API contract tests for the chat and message endpoints."""
import pytest
from fastapi import status
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

class TestAPIContracts:
    """Test cases for API contracts."""
    
    async def test_create_chat_contract(self, async_client: AsyncClient):
        """Test the contract for creating a new chat."""
        # Test valid request
        chat_data = {
            "client_name": "Test User",
            "client_email": "test@example.com"
        }
        
        response = await async_client.post("/api/chats/", json=chat_data)
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify response schema
        data = response.json()
        assert "id" in data
        assert isinstance(data["id"], str)
        assert data["client_name"] == chat_data["client_name"]
        assert data["client_email"] == chat_data["client_email"]
        assert "created_at" in data
        assert "updated_at" in data
        assert "transferred_to_operator" in data
        assert isinstance(data["transferred_to_operator"], bool)
        
        # Test validation - missing required fields
        response = await async_client.post("/api/chats/", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test validation - invalid email
        response = await async_client.post(
            "/api/chats/", 
            json={"client_name": "Test", "client_email": "invalid-email"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_send_message_contract(self, async_client: AsyncClient):
        """Test the contract for sending a message."""
        # First, create a chat
        chat_response = await async_client.post(
            "/api/chats/", 
            json={"client_name": "Test", "client_email": "test@example.com"}
        )
        chat_id = chat_response.json()["id"]
        
        # Test valid message
        message_data = {
            "content": "Hello, bot!",
            "sender": "client",
            "intent": "greeting"
        }
        
        response = await async_client.post(
            f"/api/chats/{chat_id}/messages",
            json=message_data
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify response schema
        data = response.json()
        assert "id" in data
        assert data["content"] == message_data["content"]
        assert data["sender"] == message_data["sender"]
        assert data["intent"] == message_data["intent"]
        assert "created_at" in data
        
        # Test validation - missing required fields
        response = await async_client.post(
            f"/api/chats/{chat_id}/messages",
            json={"content": "test"}  # missing sender and intent
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test validation - invalid sender
        response = await async_client.post(
            f"/api/chats/{chat_id}/messages",
            json={
                "content": "test",
                "sender": "invalid_sender",
                "intent": "greeting"
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Test validation - invalid intent
        response = await async_client.post(
            f"/api/chats/{chat_id}/messages",
            json={
                "content": "test",
                "sender": "client",
                "intent": "invalid_intent"
            }
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    async def test_get_messages_contract(self, async_client: AsyncClient):
        """Test the contract for retrieving messages."""
        # First, create a chat and a message
        chat_response = await async_client.post(
            "/api/chats/", 
            json={"client_name": "Test", "client_email": "test@example.com"}
        )
        chat_id = chat_response.json()["id"]
        
        # Add a message
        await async_client.post(
            f"/api/chats/{chat_id}/messages",
            json={
                "content": "Test message",
                "sender": "client",
                "intent": "greeting"
            }
        )
        
        # Test getting messages
        response = await async_client.get(f"/api/messages/?chat_id={chat_id}")
        assert response.status_code == status.HTTP_200_OK
        
        # Verify response schema
        data = response.json()
        assert isinstance(data, list)
        if data:  # If there are messages
            message = data[0]
            assert "id" in message
            assert "content" in message
            assert "sender" in message
            assert "intent" in message
            assert "created_at" in message
        
        # Test with invalid chat_id
        response = await async_client.get("/api/messages/?chat_id=invalid-uuid")
        assert response.status_code == status.HTTP_200_OK  # Should return empty list, not an error
        assert response.json() == []
