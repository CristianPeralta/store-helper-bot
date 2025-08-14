"""Tests for the ChatProcessor class."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.chat_processor import ChatProcessor
from app.schemas.message import MessageCreate, SenderEnum, IntentEnum
from app.db.models.message import Message

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
class TestChatProcessorService:
    """Test cases for the ChatProcessor class."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock(spec=AsyncSession)
        return session
    
    @pytest.fixture
    def chat_processor(self, mock_db_session):
        """Create a ChatProcessor instance with a mock database session."""
        return ChatProcessor(mock_db_session)
    
    @pytest.fixture
    def test_state(self):
        """Create a test conversation state."""
        return {
            "chat_id": "test-chat-123",
            "messages": []
        }
    
    @pytest.fixture
    def test_user_message(self):
        """Create a test user message."""
        message = Message(
            id=1,
            chat_id="test-chat-123",
            content="Hello, bot!",
            sender=SenderEnum.CLIENT,
            intent=IntentEnum.GREETING
        )
        return message
    
    @pytest.fixture
    def mock_assistant_response(self):
        """Create a mock assistant response."""
        return {
            "content": "Hello! How can I help you today?",
            "intent": "GREETING"
        }

    async def test_process_message_success(self, chat_processor, test_state, test_user_message, mock_assistant_response):
        """Test successful message processing."""
        # Mock the assistant's get_response method
        chat_processor.assistant.get_response_by_thread_id = AsyncMock(return_value=mock_assistant_response)
        
        # Mock the message service's create method
        chat_processor._save_bot_response = AsyncMock(return_value=Message(
            id=2,
            chat_id=test_state["chat_id"],
            content=mock_assistant_response["content"],
            sender=SenderEnum.BOT,
            intent=IntentEnum.GREETING
        ))
        
        # Call the method under test
        result = await chat_processor.process_message(test_state, test_user_message)
        
        # Verify the result
        assert result["success"] is True
        assert result["user_message"] == test_user_message
        assert result["bot_message"].content == mock_assistant_response["content"]
        
        # Verify the state was updated
        assert len(test_state["messages"]) == 2
        assert test_state["messages"][0] == {"role": "user", "content": test_user_message.content}
        assert test_state["messages"][1] == {"role": "assistant", "content": mock_assistant_response["content"]}
    
    async def test_process_message_error(self, chat_processor, test_state, test_user_message):
        """Test error handling during message processing."""
        # Make the assistant raise an exception
        chat_processor.assistant.get_response_by_thread_id = AsyncMock(side_effect=Exception("Test error"))
        
        # Call the method under test
        result = await chat_processor.process_message(test_state, test_user_message)
        
        # Verify the error response
        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "Test error"
    
    async def test_parse_response_valid(self, chat_processor):
        """Test parsing a valid assistant response."""
        response = {
            "content": "Hello!",
            "intent": "GREETING"
        }
        
        content, intent = chat_processor._parse_response(response)
        
        assert content == "Hello!"
        assert intent == IntentEnum.GREETING
    
    async def test_parse_response_invalid_content(self, chat_processor):
        """Test parsing a response with invalid content."""
        response = {
            "content": "",
            "intent": "GREETING"
        }
        
        content, _ = chat_processor._parse_response(response)
        assert "I couldn't generate a response" in content
    
    async def test_parse_response_invalid_intent(self, chat_processor):
        """Test parsing a response with an invalid intent."""
        response = {
            "content": "Hello!",
            "intent": "INVALID_INTENT"
        }
        
        _, intent = chat_processor._parse_response(response)
        assert intent == IntentEnum.OTHER
