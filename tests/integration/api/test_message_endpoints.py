"""Integration tests for message API endpoints."""
import uuid
import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat import Chat, Intent as ChatIntent
from app.db.models.message import Message, Sender, Intent as MessageIntent
from app.schemas.message import SenderEnum, IntentEnum

# Configure warning filters at the module level
pytestmark = [
    pytest.mark.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module=r"pydantic.*"
    ),
    pytest.mark.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module=r"fireworks.*"
    )
]

@pytest.mark.asyncio
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
        # Create a test chat
        chat = Chat(
            client_name="Test User",
            client_email="test@example.com",
            initial_intent=ChatIntent.GENERAL_QUESTION
        )
        db_session.add(chat)
        await db_session.flush()
        chat_id = str(chat.id)
        
        # Create messages with different timestamps
        messages = [
            Message(chat_id=chat_id, content="First", sender=Sender.CLIENT, intent=MessageIntent.GREETING),
            Message(chat_id=chat_id, content="Second", sender=Sender.BOT, intent=MessageIntent.GREETING),
            Message(chat_id=chat_id, content="Third", sender=Sender.CLIENT, intent=MessageIntent.GREETING),
        ]
        db_session.add_all(messages)
        await db_session.commit()
        
        # Clear the session to avoid transaction issues
        await db_session.close()
        
        # Test ascending order
        response = await async_client.get(f"/api/messages/?chat_id={chat_id}&sort_order=asc")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        # Verify messages are sorted by created_at in ascending order
        timestamps = [msg["created_at"] for msg in data]
        assert timestamps == sorted(timestamps)
        
        # Test descending order
        response = await async_client.get(f"/api/messages/?chat_id={chat_id}&sort_order=desc")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        # Verify messages are sorted by created_at in descending order
        timestamps = [msg["created_at"] for msg in data]
        assert timestamps == sorted(timestamps, reverse=True)
    
    async def test_get_messages_pagination(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test message retrieval with pagination."""
        # Create a test chat
        chat = Chat(
            client_name="Test User",
            client_email="test@example.com",
            initial_intent=ChatIntent.GENERAL_QUESTION
        )
        db_session.add(chat)
        await db_session.flush()
        chat_id = str(chat.id)
        
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
        
        # Clear the session to avoid transaction issues
        await db_session.close()
        
        # Test first page
        response = await async_client.get(f"/api/messages/?chat_id={chat_id}&limit=5&skip=0")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 5
        
        # Test second page
        response = await async_client.get(f"/api/messages/?chat_id={chat_id}&limit=5&skip=5")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 5
        
        # Test third page (partial)
        response = await async_client.get(f"/api/messages/?chat_id={chat_id}&limit=5&skip=10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 5 
    
    async def test_get_messages_empty(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test retrieving messages when none exist."""
        # Create a test chat to get a valid chat_id
        chat = Chat(
            client_name="Test User",
            client_email="test@example.com",
            initial_intent=ChatIntent.GENERAL_QUESTION
        )
        db_session.add(chat)
        await db_session.flush()
        chat_id = str(chat.id)
        
        # Clear the session to avoid transaction issues
        await db_session.close()
        
        response = await async_client.get(f"/api/messages/?chat_id={chat_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_create_message_success(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test creating a new message successfully."""
        # Create a test chat first
        chat = Chat(
            client_name="Test User",
            client_email="test@example.com",
            initial_intent=ChatIntent.GENERAL_QUESTION
        )
        db_session.add(chat)
        await db_session.flush()
        chat_id = str(chat.id)
        
        # Prepare message data
        message_data = {
            "chat_id": chat_id,
            "content": "Hello, this is a test message",
            "sender": SenderEnum.CLIENT.value,
            "intent": IntentEnum.GREETING.value
        }
        
        # Send POST request
        response = await async_client.post("/api/messages/", json=message_data)
        
        # Verify response
        assert response.status_code == status.HTTP_201_CREATED
        response_data = response.json()
        assert "data" in response_data
        
        # Verify message data in response
        message = response_data["data"]
        assert message["chat_id"] == chat_id
        assert message["content"] == message_data["content"]
        assert message["sender"] == message_data["sender"]
        assert message["intent"] == message_data["intent"]
        assert "id" in message
        assert "created_at" in message
        
        # Verify message was saved in the database
        db_response = await async_client.get(f"/api/messages/?chat_id={chat_id}")
        assert db_response.status_code == status.HTTP_200_OK
        messages = db_response.json()
        
        # There should be 2 messages: the user's message and the bot's response
        assert len(messages) == 2
        
        # The first message should be the one we just created
        assert messages[0]["id"] == message["id"]
        assert messages[0]["content"] == message_data["content"]
        assert messages[0]["sender"] == message_data["sender"]
        
        # The second message should be the bot's response
        assert messages[1]["sender"] == "BOT"
        assert messages[1]["chat_id"] == chat_id
    
    async def test_create_message_nonexistent_chat(self, async_client: AsyncClient):
        """Test creating a message with a non-existent chat ID."""
        # Prepare message data with non-existent chat ID
        message_data = {
            "chat_id": str(uuid.uuid4()),
            "content": "This should fail",
            "sender": SenderEnum.CLIENT.value,
            "intent": IntentEnum.GREETING.value
        }
        
        # Send POST request
        response = await async_client.post("/api/messages/", json=message_data)
        
        # Verify error response
        assert response.status_code == status.HTTP_404_NOT_FOUND
        error_data = response.json()
        assert "detail" in error_data
        assert "not found" in error_data["detail"].lower()
    
    async def test_create_message_invalid_data(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test creating a message with invalid data."""
        # Create a test chat first
        chat = Chat(
            client_name="Test User",
            client_email="test@example.com",
            initial_intent=ChatIntent.GENERAL_QUESTION
        )
        db_session.add(chat)
        await db_session.flush()
        chat_id = str(chat.id)
        
        # Test cases for invalid data
        test_cases = [
            (
                {"content": "", "sender": SenderEnum.CLIENT.value},  # Empty content
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            (
                {"content": "a" * 2001, "sender": SenderEnum.CLIENT.value},  # Content too long
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            (
                {"content": "Valid content", "sender": "INVALID_SENDER"},  # Invalid sender
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            (
                {"content": "Valid content", "sender": SenderEnum.CLIENT.value, "intent": "INVALID_INTENT"},  # Invalid intent
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            (
                {"sender": SenderEnum.CLIENT.value},  # Missing content
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            (
                {"content": "Valid content"},  # Missing sender
                status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        ]
        
        for data, expected_status in test_cases:
            # Add chat_id to the test data
            test_data = {"chat_id": chat_id, **data}
            response = await async_client.post("/api/messages/", json=test_data)
            assert response.status_code == expected_status, f"Failed for data: {test_data}"
    
    async def test_create_message_background_processing(self, async_client: AsyncClient, db_session: AsyncSession, mocker):
        """Test that message processing is triggered in the background."""
        # Create a test chat
        chat = Chat(
            client_name="Test User",
            client_email="test@example.com",
            initial_intent=ChatIntent.GENERAL_QUESTION
        )
        db_session.add(chat)
        await db_session.flush()
        chat_id = str(chat.id)
        
        # Mock the ChatProcessor.process_message method
        mock_process = mocker.patch(
            'app.services.chat_processor.ChatProcessor.process_message',
            return_value=None
        )
        
        # Create a client message (should trigger background processing)
        message_data = {
            "chat_id": chat_id,
            "content": "Hello, process this message",
            "sender": SenderEnum.CLIENT.value,
            "intent": IntentEnum.GREETING.value
        }
        
        response = await async_client.post("/api/messages/", json=message_data)
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify the background task was scheduled
        mock_process.assert_called_once()
        
        # Create a bot message (should not trigger background processing)
        bot_message_data = {
            "chat_id": chat_id,
            "content": "This is a bot response",
            "sender": SenderEnum.BOT.value,
            "intent": IntentEnum.GREETING.value
        }
        
        mock_process.reset_mock()
        response = await async_client.post("/api/messages/", json=bot_message_data)
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify no background task was scheduled for bot messages
        mock_process.assert_not_called()
    
    async def test_get_messages_invalid_sort_field(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test that invalid sort fields are handled gracefully."""
        # Create a test chat to get a valid chat_id
        chat = Chat(
            client_name="Test User",
            client_email="test@example.com",
            initial_intent=ChatIntent.GENERAL_QUESTION
        )
        db_session.add(chat)
        await db_session.flush()
        chat_id = str(chat.id)
        
        # Create some test messages
        messages = [
            Message(chat_id=chat_id, content="Test 1", sender=Sender.CLIENT, intent=MessageIntent.GREETING),
            Message(chat_id=chat_id, content="Test 2", sender=Sender.BOT, intent=MessageIntent.GREETING),
        ]
        db_session.add_all(messages)
        await db_session.commit()
        
        # Clear the session to avoid transaction issues
        await db_session.close()
        
        # Test with an invalid sort field
        # The API currently accepts any string for sort_by, so we'll verify it doesn't cause an error
        response = await async_client.get(f"/api/messages/?chat_id={chat_id}&sort_by=nonexistent_field")
        
        # The API should still return 200 OK even with an invalid sort field
        # as it falls back to default sorting
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        
        # Verify we still get the messages back
        assert len(data) == 2
