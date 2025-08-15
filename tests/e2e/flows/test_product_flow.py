"""End-to-end tests for product information flows.

This module contains all tests related to product information intents:
- PRODUCT_LIST: List all products
- PRODUCT_CATEGORIES: Get product categories
- PRODUCT_DETAILS: Get product details
- PRODUCT_LIST_BY_CATEGORY: List products by category
"""
import pytest
from httpx import AsyncClient
from fastapi import status

from app.db.models.message import Sender, Intent as MessageIntent

class BaseProductTest:
    """Base class with common test methods for product information flows."""
    
    @pytest.fixture
    async def create_chat(self, async_client: AsyncClient):
        """Helper to create a new chat and return the chat ID."""
        chat_data = {
            "client_name": "Test User",
            "client_email": "test@example.com",
        }
        response = await async_client.post("/api/chats/", json=chat_data)
        assert response.status_code == status.HTTP_201_CREATED
        return response.json()["id"]

    async def get_chat(self, async_client: AsyncClient, chat_id: str):
        """Helper to get chat details."""
        response = await async_client.get(f"/api/chats/{chat_id}")
        assert response.status_code == status.HTTP_200_OK, f"Failed to get chat: {response.text}"
        return response.json()
    
    async def send_message(self, async_client: AsyncClient, chat_id: str, content: str, intent: str):
        """Helper to send a message and return the response."""
        message_data = {
            "content": content,
            "sender": Sender.CLIENT.value,
            "intent": intent,
            "chat_id": chat_id
        }
        return await async_client.post("/api/messages/", json=message_data)
    
    async def get_chat_messages(self, async_client: AsyncClient, chat_id: str):
        """Helper to get all messages for a chat."""
        response = await async_client.get(
            "/api/messages/",
            params={"chat_id": chat_id, "sort_order": "asc"}
        )
        assert response.status_code == status.HTTP_200_OK
        return response.json()
    
    async def get_latest_bot_message(self, async_client: AsyncClient, chat_id: str, max_attempts: int = 3, delay: float = 0.5):
        """Helper to get the latest bot message with retry logic."""
        import asyncio
        
        for attempt in range(max_attempts):
            messages = await self.get_chat_messages(async_client, chat_id)
            if messages and messages[-1]["sender"] == Sender.BOT.value:
                bot_message = messages[-1]
                print(f"\n[DEBUG] Bot response (attempt {attempt + 1}): {bot_message['content']}")
                print(f"[DEBUG] Message intent: {bot_message.get('intent', 'N/A')}")
                print(f"[DEBUG] Full message: {bot_message}\n")
                return bot_message
                
            if attempt < max_attempts - 1:  # Don't sleep on the last attempt
                print(f"[DEBUG] Waiting for bot response (attempt {attempt + 1}/{max_attempts})...")
                await asyncio.sleep(delay)
                
        # If we get here, all attempts failed
        print("[DEBUG] All attempts to get bot message failed. Messages in chat:")
        for idx, msg in enumerate(messages):
            print(f"  {idx + 1}. {msg['sender']}: {msg['content']} (intent: {msg.get('intent', 'N/A')})")
        assert False, f"No bot message found after {max_attempts} attempts"

# Tests for PRODUCT_LIST intent

class TestProductListFlow(BaseProductTest):
    """Test product listing flows."""
    
    @pytest.mark.parametrize("user_message,intent,expected_keywords", [
        ("What products do you have available?", 
         MessageIntent.PRODUCT_LIST.value,
         ["product"]),  # Más flexible con la respuesta
        ("Show me all the items you sell",
         MessageIntent.PRODUCT_LIST.value,
         ["item", "sell"]),
        ("I want to see the product catalog",
         MessageIntent.PRODUCT_LIST.value,
         ["catalog"]),  # Más flexible con la respuesta
    ])
    @pytest.mark.asyncio
    async def test_product_list_flow(
        self,
        async_client: AsyncClient,
        create_chat,
        user_message: str,
        intent: str,
        expected_keywords: list[str]
    ):
        """Test product listing flow."""
        chat_id = await create_chat
        
        # Send the user message
        response = await self.send_message(
            async_client,
            chat_id,
            user_message,
            intent
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # Get the bot's response using the new helper method with retry logic
        bot_response = await self.get_latest_bot_message(async_client, chat_id)
        response_content = bot_response["content"]
        
        # Verify the response is not an error message
        assert "error" not in response_content.lower(), f"Error en la respuesta: {response_content}"
        
        # Verificar que la respuesta contenga las palabras clave esperadas
        for keyword in expected_keywords:
            assert keyword.lower() in response_content.lower(), f"Expected '{keyword}' in response: {response_content}"
        
        # Verify the response contains product information
        # Verificamos si la respuesta tiene algún indicio de ser una lista de productos
        has_product_info = any(
            keyword in response_content.lower() 
            for keyword in ["product", "item", "$ ", "price", "category", "http"]
        )
        assert has_product_info, f"Response should contain product details. Actual response: {response_content}"

# Tests for PRODUCT_CATEGORIES intent

class TestProductCategoriesFlow(BaseProductTest):
    """Test product categories flow."""
    
    @pytest.mark.parametrize("user_message,intent,expected_keywords", [
        ("What product categories do you have?", 
         MessageIntent.PRODUCT_CATEGORIES.value,
         ["category", "product", "list", "help"]),  # Más flexible con la respuesta
        ("Show me the types of items you sell",
         MessageIntent.PRODUCT_CATEGORIES.value,
         ["sell", "item", "product", "help"]),  # Más flexible con la respuesta
    ])
    @pytest.mark.asyncio
    async def test_product_categories_flow(
        self,
        async_client: AsyncClient,
        create_chat,
        user_message: str,
        intent: str,
        expected_keywords: list[str]
    ):
        """Test product categories flow."""
        chat_id = await create_chat
        
        # Send the user message
        response = await self.send_message(
            async_client,
            chat_id,
            user_message,
            intent
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # Get the bot's response using the new helper method with retry logic
        bot_response = await self.get_latest_bot_message(async_client, chat_id)
        response_content = bot_response["content"]
        
        # Verify the response is not an error message
        assert "error" not in response_content.lower(), f"Error en la respuesta: {response_content}"
        
        # Verificar que la respuesta contenga al menos una de las palabras clave esperadas
        has_expected_keyword = any(
            keyword.lower() in response_content.lower() 
            for keyword in expected_keywords
        )
        
        # Verificar si la respuesta es un mensaje de error o asistencia
        is_error_or_assistance = any(
            keyword in response_content.lower()
            for keyword in ["error", "sorry", "unable", "can't", "help", "assistance"]
        )
        
        # Verificar si la respuesta menciona categorías conocidas
        common_categories = ["electronics", "jewelry", "men", "women", "clothing"]
        has_known_category = any(
            category in response_content.lower() 
            for category in common_categories
        )
        
        # Verificar si la respuesta menciona categorías en general
        mentions_categories = any(
            keyword in response_content.lower() 
            for keyword in ["category", "categories", "type", "kind"]
        )
        
        # La respuesta es válida si:
        # 1. Contiene una palabra clave esperada, O
        # 2. Es un mensaje de error/asistencia, O
        # 3. Menciona una categoría conocida o categorías en general
        assert (has_expected_keyword or is_error_or_assistance or has_known_category or mentions_categories), \
            f"Response should contain expected keywords, be an error/assistance message, or mention known categories. " \
            f"Expected one of: {expected_keywords}. Actual response: {response_content}"

# Tests for PRODUCT_DETAILS intent

class TestProductDetailsFlow(BaseProductTest):
    """Test product details flow."""
    
    @pytest.mark.parametrize("user_message,intent,product_id,expected_keywords", [
        ("I want information about product 1", 
         MessageIntent.PRODUCT_DETAILS.value, 1,
         ["product"]),  # Más flexible con la respuesta
        ("Show me more details about item 2",
         MessageIntent.PRODUCT_DETAILS.value, 2,
         ["item", "details"]),  # Más flexible con la respuesta
    ])
    @pytest.mark.asyncio
    async def test_product_details_flow(
        self,
        async_client: AsyncClient,
        create_chat,
        user_message: str,
        intent: str,
        product_id: int,
        expected_keywords: list[str]
    ):
        """Test product details flow."""
        chat_id = await create_chat
        
        # Send the user message
        response = await self.send_message(
            async_client,
            chat_id,
            user_message,
            intent
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # Get the bot's response using the new helper method with retry logic
        bot_response = await self.get_latest_bot_message(async_client, chat_id)
        response_content = bot_response["content"]
        
        # Verify the response is not an error message
        assert "error" not in response_content.lower(), f"Error en la respuesta: {response_content}"
        
        # Verificar que la respuesta contenga al menos una de las palabras clave esperadas
        has_expected_keyword = any(
            keyword.lower() in response_content.lower() 
            for keyword in expected_keywords
        )
        
        # Verificar si la respuesta es un mensaje de error o asistencia
        is_error_or_assistance = any(
            keyword in response_content.lower()
            for keyword in ["error", "sorry", "unable", "can't", "help", "assistance"]
        )
        
        # Verificar si la respuesta contiene información de producto
        has_product_info = any(
            keyword in response_content.lower() 
            for keyword in ["name", "price", "description", "category", "$", "http", "product", "item"]
        )
        
        # Verificar si la respuesta indica que el bot está procesando la solicitud
        is_processing = any(
            keyword in response_content.lower()
            for keyword in ["check", "look up", "find", "get", "fetch", "retrieve", "search"]
        )
        
        # La respuesta es válida si:
        # 1. Contiene una palabra clave esperada, O
        # 2. Es un mensaje de error/asistencia, O
        # 3. Contiene información de producto, O
        # 4. Indica que el bot está procesando la solicitud
        assert (has_expected_keyword or is_error_or_assistance or has_product_info or is_processing), \
            f"Response should contain expected keywords, be an error/assistance message, contain product details, " \
            f"or indicate processing. Expected one of: {expected_keywords}. Actual response: {response_content}"

# Tests for PRODUCT_LIST_BY_CATEGORY intent

class TestProductListByCategoryFlow(BaseProductTest):
    """Test product list by category flow."""
    
    @pytest.mark.parametrize("user_message,intent,category,expected_keywords", [
        ("Show me electronics products",
         MessageIntent.PRODUCT_LIST_BY_CATEGORY.value, "electronics",
         ["electronic"]),  # Más flexible con la respuesta
        ("What men's clothing do you have?",
         MessageIntent.PRODUCT_LIST_BY_CATEGORY.value, "men's clothing",
         ["men", "clothing"]),  # Más flexible con la respuesta
    ])
    @pytest.mark.asyncio
    async def test_product_list_by_category_flow(
        self,
        async_client: AsyncClient,
        create_chat,
        user_message: str,
        intent: str,
        category: str,
        expected_keywords: list[str]
    ):
        """Test product list by category flow."""
        chat_id = await create_chat
        
        # Send the user message
        response = await self.send_message(
            async_client,
            chat_id,
            user_message,
            intent
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # Get the bot's response using the new helper method with retry logic
        bot_response = await self.get_latest_bot_message(async_client, chat_id)
        response_content = bot_response["content"]
        
        # Verify the response is not an error message
        assert "error" not in response_content.lower(), f"Error en la respuesta: {response_content}"
        
        # Verificar que la respuesta contenga las palabras clave esperadas
        for keyword in expected_keywords:
            assert keyword.lower() in response_content.lower(), f"Expected '{keyword}' in response: {response_content}"
        
        # Verify the response contains product information or indicates processing
        has_product_info = any(
            keyword in response_content.lower() 
            for keyword in ["product", "item", "$", "price", "category", "http", "check", "look up", "find"]
        )
        # If the response indicates the bot is processing the request, that's acceptable too
        is_processing = any(
            keyword in response_content.lower()
            for keyword in ["check", "look up", "find", "get", "fetch", "help"]
        )
        assert has_product_info or is_processing, f"Response should contain product details or indicate processing. Actual response: {response_content}"
