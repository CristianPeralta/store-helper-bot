"""Unit tests for the StoreAssistant class in app/langchain/model.py."""
import warnings
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from typing import Dict, Any

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

from app.langchain.model import StoreAssistant, State


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_llm():
    """Create a mock language model."""
    mock = MagicMock()
    mock.bind_tools.return_value = mock
    return mock


@pytest.fixture
def mock_tool_manager():
    """Create a mock tool manager."""
    mock = MagicMock()
    mock.tools = ["tool1", "tool2"]  # Simplified tools for testing
    return mock


class TestStoreAssistant:
    """Test cases for the StoreAssistant class."""

    @patch('app.langchain.model.init_chat_model')
    @patch('app.langchain.model.ToolNode')
    @patch('app.langchain.model.StateGraph')
    def test_initialization(self, mock_state_graph, mock_tool_node, mock_init, mock_db):
        """Test that StoreAssistant initializes correctly."""
        # Setup
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_init.return_value = mock_llm
        
        # Mock the graph building
        mock_graph = MagicMock()
        mock_state_graph.return_value = mock_graph
        
        # Mock the tool node
        mock_node = MagicMock()
        mock_tool_node.return_value = mock_node
        
        # Execute
        assistant = StoreAssistant(db=mock_db)
        
        # Assert
        mock_init.assert_called_once_with(
            "accounts/fireworks/models/qwen3-30b-a3b", 
            model_provider="fireworks"
        )
        assert assistant.llm is not None
        assert assistant.llm_with_tools is not None
        assert assistant.graph is not None
        assert assistant.system_message is None

    def test_get_system_message(self, mock_db):
        """Test that _get_system_message returns the expected format."""
        # Setup
        chat_id = "test-chat-123"
        assistant = StoreAssistant(db=mock_db)
        
        # Execute
        message = assistant._get_system_message(chat_id=chat_id)
        
        # Assert
        assert isinstance(message, dict)
        assert message["role"] == "system"
        assert "content" in message
        assert chat_id in message["content"]
        assert "GENERAL_QUESTION" in message["content"]
        assert "GREETING" in message["content"]
        assert "STORE_INFO" in message["content"]

    @pytest.mark.asyncio
    async def test_chatbot(self, mock_db):
        """Test the chatbot method processes messages correctly."""
        # Setup - create a proper async mock class with all required methods
        class AsyncMockLLM:
            def __init__(self):
                self.content = '{"reply": "Hello!", "intent": "GREETING"}'
            
            async def ainvoke(self, *args, **kwargs):
                return self
                
            def bind_tools(self, tools):
                # Return self to allow chaining
                return self
        
        # Create the mock LLM instance
        mock_llm = AsyncMockLLM()
        
        with patch('app.langchain.model.init_chat_model', return_value=mock_llm):
            # Create a minimal working assistant
            assistant = StoreAssistant(db=mock_db)
            
            # Create a simple state that matches the State TypedDict
            state = {
                "messages": [{"role": "user", "content": "Hi!"}],
                "chat_id": "test-chat-123",
                "name": "Test User",
                "email": "test@example.com",
                "last_inquiry_id": None
            }
            
            # Execute
            result = await assistant.chatbot(state)
            
            # Assert
            assert "messages" in result
            assert len(result["messages"]) == 1
            assert result["messages"][0].content == '{"reply": "Hello!", "intent": "GREETING"}'

    @pytest.mark.parametrize("input_content,expected_reply,expected_intent", [
        ('{"reply": "Hello!", "intent": "GREETING"}', 
         "Hello!", "GREETING"),
        ('```json\n{"reply": "Hello!", "intent": "GREETING"}\n```', 
         "Hello!", "GREETING"),
        ('Some text before\n```json\n{"reply": "Hello!", "intent": "GREETING"}\n```\nSome text after', 
         "Hello!", "GREETING"),
        ('No JSON here', "Invalid or missing JSON", "OTHER"),
        ('', "Empty response", "OTHER"),
    ])
    def test_get_json_content(self, mock_db, input_content, expected_reply, expected_intent):
        """Test JSON content extraction from various input formats."""
        # Setup
        assistant = StoreAssistant(db=mock_db)
        
        # Execute
        result = assistant.get_json_content(input_content)
        
        # Assert
        assert isinstance(result, dict)
        assert "reply" in result
        assert "intent" in result
        assert result["reply"] == expected_reply
        assert result["intent"] == expected_intent

    @pytest.mark.asyncio
    async def test_ensure_system_message(self, mock_db):
        """Test that system message is added correctly."""
        # Setup
        assistant = StoreAssistant(db=mock_db)
        chat_id = "test-chat-123"
        state = State(
            messages=[{"role": "user", "content": "Hi!"}],
            chat_id=chat_id,
            name="Test User",
            email="test@example.com",
            last_inquiry_id=None
        )
        
        # Execute
        await assistant._ensure_system_message(state, chat_id)
        
        # Assert
        assert assistant.system_message is not None
        assert len(state["messages"]) == 2
        assert state["messages"][0] == assistant.system_message
        assert state["messages"][1] == {"role": "user", "content": "Hi!"}

    @pytest.mark.asyncio
    async def test_get_response_by_thread_id(self, mock_db):
        """Test the main response generation method."""
        # Setup
        mock_llm = MagicMock()
        
        # Create a proper async mock for the graph
        class AsyncMockGraph:
            async def ainvoke(self, state, config=None):
                # Return a mock response matching the expected format
                return {
                    "messages": [
                        MagicMock(content='{"reply": "Hello!", "intent": "GREETING"}')
                    ]
                }
        
        with patch('app.langchain.model.init_chat_model', return_value=mock_llm):
            assistant = StoreAssistant(db=mock_db)
            
            # Set up the mock graph
            mock_graph = AsyncMockGraph()
            assistant.graph = mock_graph
            
            # Create a proper state dictionary
            thread_id = "test-thread-123"
            initial_state = {
                "messages": [{"role": "user", "content": "Hi!"}],
                "chat_id": thread_id,
                "name": "Test User",
                "email": "test@example.com",
                "last_inquiry_id": None
            }
            
            # Call the method with the initial state
            result = await assistant.get_response_by_thread_id(
                thread_id=thread_id,
                state=initial_state
            )
            
            # Assert
            assert result["content"] == "Hello!"
            assert result["intent"] == "GREETING"
            assert "state" in result
            # Verify the state contains messages
            assert len(result["state"].get("messages", [])) > 0  # System message should be added
