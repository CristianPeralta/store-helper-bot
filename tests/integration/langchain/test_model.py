"""Integration tests for the StoreAssistant class."""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.langchain.model import StoreAssistant, State
from app.db.models.chat import Chat, Intent as ChatIntent
from app.db.models.message import Message, Sender, Intent as MessageIntent
from app.schemas.chat import ChatCreate
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

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

# Sample test data
SAMPLE_CHAT_ID = "test-chat-123"
SAMPLE_NAME = "Test User"
SAMPLE_EMAIL = "test@example.com"
SAMPLE_QUERY = "What are your store hours?"

MOCK_GREETING_RESPONSE = {
    "reply": "Hello! How can I assist you today?",
    "intent": "greeting"
}

MOCK_STORE_HOURS_RESPONSE = {
    "reply": "Our store is open from 9 AM to 9 PM every day.",
    "intent": "store_hours"
}

# Mock tools for testing
@tool
def mock_get_store_data(store_id: str) -> str:
    """Mock function to get store data."""
    return f"Store data for {store_id}"

@tool
def mock_get_products_data(query: str) -> str:
    """Mock function to get products data."""
    return f"Products matching {query}"

# Mock ChatService
class MockChatService:
    @staticmethod
    async def get_chat(chat_id: str):
        mock_chat = AsyncMock()
        mock_chat.id = chat_id
        return mock_chat
    
    @staticmethod
    async def get_messages_by_chat_id(chat_id: str):
        return [
            {"id": "msg1", "content": "Hello!", "sender": "user", "created_at": "2023-01-01T00:00:00"},
            {"id": "msg2", "content": "Hi there!", "sender": "assistant", "created_at": "2023-01-01T00:00:01"}
        ]

@pytest.mark.asyncio
class TestStoreAssistant:
    """Test cases for the StoreAssistant class."""

    @pytest.fixture
    async def mock_db_session(self, db_session):
        """Create a mock database session with test data."""
        # Add test data to the database
        chat = Chat(id=SAMPLE_CHAT_ID)
        db_session.add(chat)
        await db_session.commit()
        yield db_session
        # Clean up
        await db_session.rollback()
    
    @pytest.fixture
    def store_assistant(self, mock_db_session):
        """Create a StoreAssistant instance with a mock database session."""
        # Patch the ToolManager to use our mock tools
        with patch('app.langchain.model.ToolManager') as mock_tool_manager:
            mock_tool_manager.return_value.tools = [mock_get_store_data, mock_get_products_data]
            # Create a new instance for each test
            assistant = StoreAssistant(db=mock_db_session)
            # Mock the LLM and graph
            assistant.llm_with_tools = AsyncMock()
            assistant.graph = AsyncMock()
            # Mock the _ensure_system_message method as an async function
            async def mock_ensure_system(state, chat_id):
                system_msg = {"role": "system", "content": f"Test system message for {chat_id}"}
                if state.get("messages"):
                    state["messages"].insert(0, system_msg)
                else:
                    state["messages"] = [system_msg]
            
            assistant._ensure_system_message = mock_ensure_system
            return assistant
    
    @pytest.fixture
    def mock_llm_response(self):
        """Create a mock LLM response."""
        def _create_mock_response(content_dict):
            return AIMessage(content=json.dumps(content_dict))
        return _create_mock_response
    
    def test_initialization(self, store_assistant):
        """Test that the StoreAssistant initializes correctly."""
        # Verify the assistant was created with the expected attributes
        assert hasattr(store_assistant, 'tools')
        assert hasattr(store_assistant, 'llm')
        assert hasattr(store_assistant, 'graph')
        assert store_assistant.system_message is None
        
        # Verify tools were initialized
        assert len(store_assistant.tools) == 2
        tool_names = [tool.name for tool in store_assistant.tools]
        # Check for the mock tool names instead of the actual implementation names
        assert "mock_get_store_data" in tool_names
        assert "mock_get_products_data" in tool_names
    
    async def test_get_system_message(self, store_assistant):
        """Test that _get_system_message returns the expected format."""
        chat_id = "test-chat-123"
        system_message = store_assistant._get_system_message(chat_id)
        
        # Verify the structure of the system message
        assert isinstance(system_message, dict)
        assert "role" in system_message
        assert system_message["role"] == "system"
        assert "content" in system_message
        assert isinstance(system_message["content"], str)
        assert "responds in JSON format" in system_message["content"]
        assert chat_id in system_message["content"]
    
    @pytest.mark.asyncio
    async def test_chatbot(self, store_assistant):
        """Test the chatbot method with a simple message."""
        # Setup test state
        test_state = {
            "messages": [
                {"role": "user", "content": "Hello!"}
            ],
            "chat_id": "test-chat",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        # Create test response
        expected_content = json.dumps({"reply": "Hello! How can I help you today?", "intent": "GREETING"})
        mock_ai_message = AIMessage(content=expected_content)
        
        # Setup mock for llm_with_tools.ainvoke
        mock_llm_with_tools = AsyncMock()
        mock_llm_with_tools.ainvoke = AsyncMock(return_value=mock_ai_message)
        
        # Replace the llm_with_tools with our mock
        original_llm_with_tools = store_assistant.llm_with_tools
        store_assistant.llm_with_tools = mock_llm_with_tools
        
        try:
            # Call the method
            result = await store_assistant.chatbot(test_state)
            
            # Verify the result
            assert isinstance(result, dict), "Should return a dictionary"
            assert "messages" in result, "Result should contain 'messages' key"
            assert len(result["messages"]) == 1, "Should return one message"
            
            # Verify the response is our mock AIMessage
            assert result["messages"][0] == mock_ai_message, "Should return the LLM response"
            
            # Verify the LLM was called with the messages
            mock_llm_with_tools.ainvoke.assert_awaited_once_with(test_state["messages"])
        finally:
            # Restore original llm_with_tools
            store_assistant.llm_with_tools = original_llm_with_tools
    
    @pytest.mark.asyncio
    @patch('app.langchain.model.init_chat_model')
    async def test_tool_invocation_flow(self, mock_init_chat, store_assistant):
        """Test the full flow of invoking a tool through the assistant."""
        # Create a mock for the tool
        mock_tool = AsyncMock()
        mock_tool.name = "mock_get_store_data"
        mock_tool.ainvoke = AsyncMock(return_value="Store 123 is open from 9 AM to 9 PM.")
        
        # Replace the tools list with our mock tool
        store_assistant.tools = [mock_tool]
        
        # Create a mock for the LLM
        mock_llm = AsyncMock()
        
        # First response: Tool call
        tool_call_response = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "mock_get_store_data",
                    "args": {"store_id": "123"},
                    "id": "call_123"
                }
            ]
        )
        
        # Second response: Final answer
        final_response = AIMessage(
            content=json.dumps({
                "reply": "The store is open from 9 AM to 9 PM.",
                "intent": "STORE_INFO"
            })
        )
        
        # Set up the side_effect to return different responses on subsequent calls
        mock_llm.ainvoke.side_effect = [tool_call_response, final_response]
        mock_init_chat.return_value = mock_llm
        
        # Create a test state
        test_state = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What are the store hours?"}
            ],
            "chat_id": "test-chat-123"
        }
        
        # Mock _ensure_system_message to avoid actual database calls
        async def mock_ensure_system(state, chat_id):
            # Ensure system message is present
            if not any(m.get("role") == "system" for m in state.get("messages", [])):
                state["messages"].insert(0, {"role": "system", "content": "You are a helpful assistant."})
            return state
        
        with patch.object(store_assistant, '_ensure_system_message', side_effect=mock_ensure_system):
            # Call the method
            result = await store_assistant.chatbot(test_state)
            
            # Verify the result
            assert isinstance(result, dict), "Result should be a dictionary"
            assert "messages" in result, "Result should contain 'messages' key"
            
            # Verify the tool was called with the correct arguments
            mock_tool.ainvoke.assert_awaited_once_with({"store_id": "123"})
            
            # Verify the LLM was called twice (once for tool call, once for final response)
            assert mock_llm.ainvoke.await_count == 2, "LLM should be called twice (tool call + final response)"
            
            # Verify the tool was invoked correctly
            mock_tool.ainvoke.assert_awaited_once_with({"store_id": "123"})
            
            # Verify the final response
            assert "messages" in result, "Result should contain 'messages' key"
            assert len(result["messages"]) > 0, "Should return at least one message"
            
            # Get the assistant's response
            response = result["messages"][-1]
            assert response["role"] == "assistant", "Last message should be from assistant"
            
            # Verify the response content is properly formatted JSON
            try:
                content = response["content"]
                if isinstance(content, str):
                    content = json.loads(content)
                
                assert isinstance(content, dict), "Content should be a dictionary"
                assert "reply" in content, "Response should contain 'reply' field"
                assert "intent" in content, "Response should contain 'intent' field"
                assert "Store 123 is open" in content["reply"], "Response should contain store hours"
            except (json.JSONDecodeError, TypeError) as e:
                pytest.fail(f"Response content is not valid JSON: {e}")
            
            # Verify the tool call was properly handled
            tool_call_args = mock_llm.ainvoke.await_args_list[0][0][0]
            assert len(tool_call_args) > 0, "Should pass messages to LLM"
            assert "tool_calls" in tool_call_args[-1], "Should include tool calls in LLM input"
    
    @pytest.mark.asyncio
    async def test_get_json_content(self, store_assistant):
        """Test JSON content extraction from various response formats."""
        # Test with valid JSON string
        valid_json = '{"reply": "Hello!", "intent": "greeting"}'
        result = store_assistant.get_json_content(valid_json)
        assert result == {"reply": "Hello!", "intent": "greeting"}
        
        # Test with JSON wrapped in code block
        code_block = '```json\n{"reply": "Hi!", "intent": "greeting"}\n```'
        result = store_assistant.get_json_content(code_block)
        assert result == {"reply": "Hi!", "intent": "greeting"}
        
        # Test with invalid JSON - should return a dict with error message
        invalid_json = 'not a json'
        result = store_assistant.get_json_content(invalid_json)
        assert isinstance(result, dict)
        assert "reply" in result
        assert "intent" in result
        assert result["intent"] == "OTHER"
        
        # Test with empty string
        result = store_assistant.get_json_content("")
        assert result == {"reply": "Empty response", "intent": "OTHER"}
    
    @pytest.mark.asyncio
    async def test_ensure_system_message(self, store_assistant):
        """Test that system message is properly set in the state."""
        # Create a test state without a system message
        state = {
            "messages": [
                {"role": "user", "content": "Hello!"}
            ],
            "chat_id": "test-chat",
            "name": "Test User",
            "email": "test@example.com"
        }
        
        # Mock the _get_system_message method
        store_assistant._get_system_message = lambda chat_id: {
            "role": "system",
            "content": f"Test system message for {chat_id}"
        }
        
        # Call the method
        await store_assistant._ensure_system_message(state, "test-chat")
        
        # Verify the system message was added
        assert len(state["messages"]) == 2, "System message should be added to the state"
        assert state["messages"][0]["role"] == "system", "First message should be the system message"
        assert "test-chat" in state["messages"][0]["content"], "Chat ID should be in the system message"
    
    @pytest.mark.asyncio
    async def test_get_response_by_thread_id(self, store_assistant):
        """Test the main method to get a response by thread ID."""
        # Setup test data
        test_chat_id = "test-chat-123"
        
        # Create a mock for the database session
        mock_db = AsyncMock()
        
        # Mock the chat query result
        mock_chat = MagicMock()
        mock_chat.id = test_chat_id
        mock_chat.client_name = "Test User"
        mock_chat.client_email = "test@example.com"
        
        # Mock the messages query result
        mock_message = MagicMock()
        mock_message.id = "msg-123"
        mock_message.chat_id = test_chat_id
        mock_message.content = json.dumps({"role": "user", "content": "Hello!"})
        mock_message.sender = "user"
        mock_message.intent = "greeting"
        mock_message.created_at = datetime.now(timezone.utc)
        
        # Configure the mock session
        mock_db.execute.return_value = mock_db
        mock_db.scalars.return_value = mock_db
        mock_db.first.side_effect = [mock_chat, mock_message]
        mock_db.all.return_value = [mock_message]
        
        # Set the mock db on the assistant
        store_assistant.db = mock_db
        
        # Mock the graph response with a proper state
        mock_ai_response = AIMessage(content=json.dumps({"reply": "Hello!", "intent": "greeting"}))
        
        # Create a proper async mock for graph.ainvoke
        async def mock_ainvoke(state, *args, **kwargs):
            # Ensure the state has all required fields
            state.update({
                "chat_id": test_chat_id,
                "name": "Test User",
                "email": "test@example.com",
                "messages": [{"role": "user", "content": "Hello!"}]
            })
            return {"messages": [mock_ai_response], "chat_id": test_chat_id}
            
        store_assistant.graph.ainvoke = mock_ainvoke
        
        # Call the method
        response = await store_assistant.get_response_by_thread_id(test_chat_id)
        
        # Verify the response
        assert isinstance(response, dict)
        assert "content" in response
        assert "intent" in response
        assert "state" in response
        assert response["intent"] == "greeting"
        
        # Verify the response state has the chat_id
        assert response["state"]["chat_id"] == test_chat_id
    
    async def test_tool_invocation_flow(self, store_assistant, mock_llm_response, mock_db_session):
        """Test the full flow of invoking a tool through the assistant."""
        # Setup test state
        test_state = State(
            messages=[
                {"role": "user", "content": "What are your store hours?"}
            ],
            chat_id="test-tool-call",
            name="Test User",
            email="test@example.com"
        )
        
        # Mock the LLM to return a tool call
        tool_call = {
            "tool_calls": [{
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "mock_get_store_data",
                    "arguments": json.dumps({"query": "store hours"})
                }
            }]
        }
        
        # Mock the LLM to first return a tool call, then a normal response
        mock_response1 = AIMessage(
            content="",
            additional_kwargs={"tool_calls": tool_call["tool_calls"]}
        )
        mock_response2 = mock_llm_response(MOCK_STORE_HOURS_RESPONSE)
        
        # Configure the LLM to return different responses on subsequent calls
        store_assistant.llm_with_tools.ainvoke.side_effect = [mock_response1, mock_response2]
        
        # Configure the graph to return our mock response
        store_assistant.graph.ainvoke.return_value = {"messages": [mock_response2]}
        
        # Call the method
        result = await store_assistant.get_response_by_thread_id(
            thread_id="test-tool-call",
            state=test_state
        )
        
        # Verify the result
        assert result["content"] == MOCK_STORE_HOURS_RESPONSE["reply"]
        assert result["intent"] == MOCK_STORE_HOURS_RESPONSE["intent"]
        assert "state" in result
