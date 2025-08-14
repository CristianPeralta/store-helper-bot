"""End-to-end tests for store information flows.

This module contains all tests related to store information intents:
- STORE_HOURS: Horario de atención
- STORE_CONTACT: Información de contacto
- STORE_PROMOTIONS: Promociones actuales
- STORE_PAYMENT_METHODS: Métodos de pago aceptados
- STORE_SOCIAL_MEDIA: Redes sociales de la tienda
- STORE_LOCATION: Ubicación de la tienda
"""
import pytest
from httpx import AsyncClient
from fastapi import status

from app.db.models.message import Sender, Intent as MessageIntent

class BaseStoreInfoTest:
    """Base class with common test methods for store information flows."""
    
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

# Tests for STORE_HOURS intent

@pytest.mark.asyncio
class TestStoreHoursFlow(BaseStoreInfoTest):
    """Test store hours information flows."""
    
    @pytest.mark.parametrize("user_message,intent,expected_keywords", [
        ("What time do you open?", MessageIntent.STORE_HOURS.value, ["open", "close", "hours"]),
        ("When are you open?", MessageIntent.STORE_HOURS.value, ["open", "close", "hours"]),
        ("What are your business hours?", MessageIntent.STORE_HOURS.value, ["open", "close", "hours"]),
    ])
    async def test_store_hours_flow(
        self, 
        async_client: AsyncClient,
        create_chat,
        user_message: str,
        intent: str,
        expected_keywords: list[str]
    ):
        """Test store hours information flow."""
        chat_id = await create_chat
        
        # Send message asking about store hours
        response = await self.send_message(
            async_client,
            chat_id,
            user_message,
            intent
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify bot's response contains store hours information
        bot_message = await self.get_latest_bot_message(async_client, chat_id)
        assert bot_message is not None, "No bot message received"
        
        response_text = bot_message["content"].lower()
        assert any(keyword in response_text for keyword in expected_keywords), \
            f"Expected bot response to contain one of {expected_keywords}. Got: {response_text}"

# Tests for STORE_CONTACT intent

@pytest.mark.asyncio
class TestStoreContactFlow(BaseStoreInfoTest):
    """Test store contact information flows."""
    
    @pytest.mark.parametrize("user_message,intent,expected_keywords", [
        ("How can I contact you?", MessageIntent.STORE_CONTACT.value, ["phone", "email", "contact"]),
        ("What's your phone number?", MessageIntent.STORE_CONTACT.value, ["phone", "number"]),
        ("What's your email?", MessageIntent.STORE_CONTACT.value, ["@", "email"]),
    ])
    async def test_store_contact_flow(
        self,
        async_client: AsyncClient,
        create_chat,
        user_message: str,
        intent: str,
        expected_keywords: list[str]
    ):
        """Test store contact information flow."""
        chat_id = await create_chat
        
        # Send message asking for contact information
        response = await self.send_message(
            async_client,
            chat_id,
            user_message,
            intent
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify bot's response contains contact information
        bot_message = await self.get_latest_bot_message(async_client, chat_id)
        assert bot_message is not None, "No bot message received"
        
        response_text = bot_message["content"].lower()
        assert any(keyword in response_text for keyword in expected_keywords), \
            f"Expected bot response to contain one of {expected_keywords}. Got: {response_text}"

"""Additional store information flow tests to be merged into the main test file."""

# Tests for STORE_PROMOTIONS intent

@pytest.mark.asyncio
class TestStorePromotionsFlow(BaseStoreInfoTest):
    """Test store promotions information flows."""
    
    @pytest.mark.parametrize("user_message,intent,expected_keywords", [
        ("Do you have any promotions?", MessageIntent.STORE_PROMOTIONS.value, 
         ["promotion", "sale", "discount"]),
        ("What deals do you have?", MessageIntent.STORE_PROMOTIONS.value, 
         ["deal", "offer", "promotion", "email"]),
    ])
    async def test_store_promotions_flow(
        self,
        async_client: AsyncClient,
        create_chat,
        user_message: str,
        intent: str,
        expected_keywords: list[str]
    ):
        """Test store promotions information flow."""
        chat_id = await create_chat
        
        # Send message asking about promotions
        response = await self.send_message(
            async_client,
            chat_id,
            user_message,
            intent
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify bot's response contains promotions information
        bot_message = await self.get_latest_bot_message(async_client, chat_id)
        assert bot_message is not None, "No bot message received"
        
        response_text = bot_message["content"].lower()
        assert any(keyword in response_text for keyword in expected_keywords), \
            f"Expected bot response to contain one of {expected_keywords}. Got: {response_text}"

# Tests for STORE_PAYMENT_METHODS intent

@pytest.mark.asyncio
class TestStorePaymentMethodsFlow(BaseStoreInfoTest):
    """Test store payment methods information flows."""
    
    @pytest.mark.parametrize("user_message,intent,expected_keywords", [
        ("What payment methods do you accept?", MessageIntent.STORE_PAYMENT_METHODS.value, 
         ["credit card", "debit", "payment", "yape", "plin", "cash", "card"]),
        ("Can I pay with PayPal?", MessageIntent.STORE_PAYMENT_METHODS.value, 
         ["paypal", "payment", "accept", "cash", "card"]),
        ("Do you take Apple Pay?", MessageIntent.STORE_PAYMENT_METHODS.value, 
         ["apple pay", "payment", "method", "cash", "card"]),
    ])
    async def test_store_payment_methods_flow(
        self,
        async_client: AsyncClient,
        create_chat,
        user_message: str,
        intent: str,
        expected_keywords: list[str]
    ):
        """Test store payment methods information flow."""
        chat_id = await create_chat
        
        # Send message asking about payment methods
        response = await self.send_message(
            async_client,
            chat_id,
            user_message,
            intent
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify bot's response contains payment methods information
        bot_message = await self.get_latest_bot_message(async_client, chat_id)
        assert bot_message is not None, "No bot message received"
        
        response_text = bot_message["content"].lower()
        assert any(keyword in response_text for keyword in expected_keywords), \
            f"Expected bot response to contain one of {expected_keywords}. Got: {response_text}"

# Tests for STORE_SOCIAL_MEDIA intent

@pytest.mark.asyncio
class TestStoreSocialMediaFlow(BaseStoreInfoTest):
    """Test store social media information flows."""
    
    @pytest.mark.parametrize("user_message,intent,expected_keywords", [
        ("Are the store on social media?", MessageIntent.STORE_SOCIAL_MEDIA.value, 
         ["facebook", "twitter", "instagram", "social"]),
        ("What's the store's Instagram?", MessageIntent.STORE_SOCIAL_MEDIA.value, 
         ["instagram", "@", "handle"]),
        ("Can I follow the store on Facebook?", MessageIntent.STORE_SOCIAL_MEDIA.value, 
         ["facebook", "page", "profile"]),
    ])
    async def test_store_social_media_flow(
        self,
        async_client: AsyncClient,
        create_chat,
        user_message: str,
        intent: str,
        expected_keywords: list[str]
    ):
        """Test store social media information flow."""
        chat_id = await create_chat
        
        # Send message asking about social media
        response = await self.send_message(
            async_client,
            chat_id,
            user_message,
            intent
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify bot's response contains social media information
        bot_message = await self.get_latest_bot_message(async_client, chat_id)
        assert bot_message is not None, "No bot message received"
        
        response_text = bot_message["content"].lower()
        assert any(keyword in response_text for keyword in expected_keywords), \
            f"Expected bot response to contain one of {expected_keywords}. Got: {response_text}"

# Tests for STORE_INFO intent

@pytest.mark.asyncio
class TestStoreInfoFlow(BaseStoreInfoTest):
    """Test general store information flows."""
    
    @pytest.mark.parametrize("user_message,intent,expected_keywords", [
        ("Tell me about your store", MessageIntent.STORE_INFO.value, 
         ["about", "store", "information"]),
        ("What can you tell me about this store?", MessageIntent.STORE_INFO.value, 
         ["about", "store", "information"]),
        ("I'd like to know more about your business", MessageIntent.STORE_INFO.value, 
         ["about", "business", "information", "products", "store", "fakestore", "fake"]),
    ])
    async def test_store_info_flow(
        self,
        async_client: AsyncClient,
        create_chat,
        user_message: str,
        intent: str,
        expected_keywords: list[str]
    ):
        """Test general store information flow."""
        chat_id = await create_chat
        
        # Send message asking about general store information
        response = await self.send_message(
            async_client,
            chat_id,
            user_message,
            intent
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify bot's response contains store information
        bot_message = await self.get_latest_bot_message(async_client, chat_id)
        assert bot_message is not None, "No bot message received"
        
        response_text = bot_message["content"].lower()
        assert any(keyword in response_text for keyword in expected_keywords), \
            f"Expected bot response to contain one of {expected_keywords}. Got: {response_text}"

# Tests for STORE_LOCATION intent

@pytest.mark.asyncio
class TestStoreLocationFlow(BaseStoreInfoTest):
    """Test store location information flows."""
    
    @pytest.mark.parametrize("user_message,intent,expected_keywords", [
        ("Where are you located?", MessageIntent.STORE_LOCATION.value, 
         ["address", "location", "map"]),
        ("What's your address?", MessageIntent.STORE_LOCATION.value, 
         ["street", "avenue", "road"]),
        ("How do I get to your store?", MessageIntent.STORE_LOCATION.value, 
         ["map", "directions", "location", "address", "lima", "peru"]),
    ])
    async def test_store_location_flow(
        self,
        async_client: AsyncClient,
        create_chat,
        user_message: str,
        intent: str,
        expected_keywords: list[str]
    ):
        """Test store location information flow."""
        chat_id = await create_chat
        
        # Send message asking about store location
        response = await self.send_message(
            async_client,
            chat_id,
            user_message,
            intent
        )
        assert response.status_code == status.HTTP_201_CREATED
        
        # Verify bot's response contains location information
        bot_message = await self.get_latest_bot_message(async_client, chat_id)
        assert bot_message is not None, "No bot message received"
        
        response_text = bot_message["content"].lower()
        assert any(keyword in response_text for keyword in expected_keywords), \
            f"Expected bot response to contain one of {expected_keywords}. Got: {response_text}"
