"""Integration tests for the ToolManager class."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.langchain.tools import ToolManager
from app.db.models.chat import Chat
from app.schemas.chat import ChatCreate

# Sample test data
SAMPLE_CHAT_ID = "test-chat-123"
SAMPLE_NAME = "Test User"
SAMPLE_EMAIL = "test@example.com"
SAMPLE_QUERY = "Test query"

@pytest.mark.asyncio
class TestToolManager:
    """Test cases for the ToolManager class."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock(spec=AsyncSession)
        return session
    
    @pytest.fixture
    def tool_manager(self, mock_db_session):
        """Create a ToolManager instance with a mock database session."""
        return ToolManager(db=mock_db_session)
    
    async def test_human_assistance_tool_success(self, tool_manager, mock_db_session):
        """Test the human_assistance tool with valid input."""
        # Mock the chat service
        mock_transfer = AsyncMock(return_value={
            "id": SAMPLE_CHAT_ID,
            "transferred_to_operator": True,
            "transfer_inquiry_id": "test-inquiry-123"
        })
        tool_manager.chat_service.transfer_to_operator = mock_transfer
        
        # Get the tool function
        human_assistance = tool_manager.tools[0]
        
        # Call the tool using the arun method for async execution
        tool_call_id = "test-tool-call-123"
        result = await human_assistance.arun({
            "name": SAMPLE_NAME,
            "email": SAMPLE_EMAIL,
            "query": SAMPLE_QUERY,
            "chat_id": SAMPLE_CHAT_ID,
            "tool_call_id": tool_call_id
        })
        
        # Verify the result
        assert isinstance(result, str)  # Should be a JSON string
        
        # Parse the result to verify its structure
        import json
        result_data = json.loads(result)
        
        assert "update" in result_data
        assert "name" in result_data["update"]
        assert "email" in result_data["update"]
        assert "last_inquiry_id" in result_data["update"]
        assert "messages" in result_data["update"]
        
        # Verify the chat service was called correctly
        mock_transfer.assert_awaited_once_with(
            db=mock_db_session,
            chat_id=SAMPLE_CHAT_ID,
            client_name=SAMPLE_NAME,
            client_email=SAMPLE_EMAIL,
            query=SAMPLE_QUERY,
            inquiry_id=result_data["update"]["last_inquiry_id"]
        )
    
    async def test_human_assistance_tool_missing_fields(self, tool_manager):
        """Test the human_assistance tool with missing required fields."""
        # Get the tool function
        human_assistance = tool_manager.tools[0]
        
        # Call the tool with missing fields using arun for async execution
        tool_call_id = "test-tool-call-123"
        result = await human_assistance.arun({
            "name": "",
            "email": "",
            "query": "",
            "chat_id": SAMPLE_CHAT_ID,
            "tool_call_id": tool_call_id
        })
        
        # Parse the result
        import json
        result_data = json.loads(result)
        
        # Verify the error response
        assert "update" in result_data
        assert "messages" in result_data["update"]
        assert isinstance(result_data["update"]["messages"], list)
        assert len(result_data["update"]["messages"]) > 0
        assert "Please provide a name, email, and query" in result_data["update"]["messages"][0]
    
    async def test_get_store_data_tool_success(self, tool_manager):
        """Test the get_store_data tool with a valid intent."""
        # Mock the store service methods
        tool_manager.store_service.get_store_info.return_value = {
            "name": "Test Store",
            "description": "A test store"
        }
        
        # Get the tool function
        get_store_data = tool_manager.tools[1]
        
        # Call the tool with a valid intent using arun for async execution
        tool_call_id = "test-tool-call-123"
        result = await get_store_data.arun({
            "intent": "store_info",
            "tool_call_id": tool_call_id
        })
        
        # Verify the result
        assert "update" in result
        assert "messages" in result["update"]
        assert "Test Store" in result["update"]["messages"][0].content
    
    async def test_get_store_data_tool_invalid_intent(self, tool_manager):
        """Test the get_store_data tool with an invalid intent."""
        # Get the tool function
        get_store_data = tool_manager.tools[1]
        
        # Call the tool with an invalid intent
        tool_call_id = "test-tool-call-123"
        result = await get_store_data.invoke({
            "intent": "invalid_intent",
            "tool_call_id": tool_call_id
        })
        
        # Verify the error response
        assert "update" in result
        assert "messages" in result["update"]
        assert "is not supported" in result["update"]["messages"][0].content
    
    async def test_get_store_data_tool_exception_handling(self, tool_manager):
        """Test exception handling in the get_store_data tool."""
        # Mock the store service to raise an exception
        tool_manager.store_service.get_store_info = MagicMock(side_effect=Exception("Test error"))
        
        # Get the tool function
        get_store_data = tool_manager.tools[1]
        
        # Call the tool
        tool_call_id = "test-tool-call-123"
        result = await get_store_data.invoke({
            "intent": "store_info",
            "tool_call_id": tool_call_id
        })
        
        # Verify the error response
        assert "update" in result
        assert "messages" in result["update"]
        assert "Error fetching store data" in result["update"]["messages"][0].content
    
    async def test_products_data_tool_success(self, tool_manager):
        """Test the products_data tool with a valid intent."""
        # Mock the product service methods
        tool_manager.product_service.get_products = AsyncMock(return_value={
            "products": [{"id": 1, "title": "Test Product"}],
            "total": 1
        })
        
        # Get the tool function
        products_data = tool_manager.tools[2]
        
        # Call the tool with a valid intent
        tool_call_id = "test-tool-call-123"
        result = await products_data.invoke({
            "intent": "list_products",
            "tool_call_id": tool_call_id,
            "limit": 5
        })
        
        # Verify the result
        assert "update" in result
        assert "messages" in result["update"]
        assert "Test Product" in result["update"]["messages"][0].content
    
    async def test_tools_initialization(self, tool_manager):
        """Test that all tools are properly initialized."""
        # Verify the expected tools are registered
        assert len(tool_manager.tools) == 3
        assert hasattr(tool_manager.tools[0], "name") and "human_assistance" in tool_manager.tools[0].name
        assert hasattr(tool_manager.tools[1], "name") and "get_store_data" in tool_manager.tools[1].name
        assert hasattr(tool_manager.tools[2], "name") and "products_data" in tool_manager.tools[2].name
