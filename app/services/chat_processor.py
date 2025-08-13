from typing import Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.message import MessageCreate, SenderEnum, MessageUpdate, IntentEnum
from app.services.message import message_service
from app.langchain.model import StoreAssistant, State
import logging

logger = logging.getLogger(__name__)

class ChatProcessor:
    """Orchestrates the processing of chat messages between users and the assistant."""
    def __init__(self, db: AsyncSession):
        self.db = db
        self.assistant = StoreAssistant(db)

    async def process_message(
        self,
        state: State,
        user_input: str,
    ) -> Dict[str, Any]:
        """
        Process a user message and generate an assistant response.

        Args:
            state: Current conversation state
            user_input: User's input message

        Returns:
            Dict containing the assistant's response and metadata
        """
        # Save user message and get the message object
        user_message = await self._save_user_message(state["chat_id"], user_input)
        
        # Add to conversation history
        state["messages"].append({"role": "user", "content": user_input})

        try:
            # Get assistant's response
            response = await self._get_assistant_response(
                state
            )
            
            # Process and save the response
            return await self._process_assistant_response(
                state, user_message, response
            )

        except Exception as e:
            logger.exception("Error processing message")
            return self._create_error_response(e)

    async def _save_user_message(
        self, chat_id: int, user_input: str
    ) -> Any:
        """Save the user's message to the database."""
        return await message_service.create(
            self.db,
            obj_in=MessageCreate(
                chat_id=chat_id,
                content=user_input,
                sender=SenderEnum.CLIENT,
            )
        )

    async def _get_assistant_response(
        self,
        state: State,
    ) -> Dict[str, Any]:
        """Get a response from the assistant."""
        return await self.assistant.get_response_by_thread_id(state["chat_id"], state)

    async def _process_assistant_response(
        self,
        state: State,
        user_message: Any,
        response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process and save the assistant's response."""
        content, intent_enum = self._parse_response(response)
        state["messages"].append({"role": "assistant", "content": content})

        await self._save_bot_response(state, content, intent_enum)

        await self._update_user_intent(user_message, intent_enum)

        print("\nBot:", content)

        return {
            "content": content,
            "intent": intent_enum.value,
            "success": True
        }

    def _parse_response(self, response: Dict[str, Any]) -> Tuple[str, IntentEnum]:
        """Parse and validate the assistant's response."""
        content = response.get("content", "")
        intent_value: IntentEnum = response.get("intent", IntentEnum.OTHER)
        
        if not isinstance(content, str) or not content:
            content = "I couldn't generate a response. Please try again or rephrase your question."
            logger.warning("Assistant returned empty or invalid content: %s", response)

        try:
            intent_enum = IntentEnum(intent_value.upper())
        except (ValueError, AttributeError):
            intent_enum = IntentEnum.OTHER

        return content, intent_enum

    async def _save_bot_response(
        self,
        state: State,
        content: str,
        intent: IntentEnum
    ) -> None:
        """Save the bot's response to the database."""
        await message_service.create(
            self.db,
            obj_in=MessageCreate(
                chat_id=state["chat_id"],
                content=content,
                sender=SenderEnum.BOT,
                intent=intent,
            )
        )

    async def _update_user_intent(
        self,
        user_message: Any,
        intent: IntentEnum
    ) -> None:
        """Update the user message with the detected intent."""
        await message_service.update(
            self.db,
            db_obj=user_message,
            obj_in=MessageUpdate(intent=intent)
        )

    def _create_error_response(self, error: Exception) -> Dict[str, Any]:
        """Create an error response dictionary."""
        return {
            "content": "Sorry, I encountered an error processing your request.",
            "intent": IntentEnum.OTHER.value,
            "success": False,
            "error": str(error)
        }

