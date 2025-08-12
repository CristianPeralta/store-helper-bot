import logging
from app.services.chat import chat_service
from app.services.message import message_service
from app.db.models.message import Sender, Intent
from app.schemas.chat import ChatCreate
from app.db.silent_session import get_db_session
from app.langchain.model import StoreAssistant

"""
Console runner for the Store Helper chatbot.

This script demonstrates how to:
- Create and persist a chat session in the DB
- Read user input from console and send it to the assistant
- Persist messages with intents
- Provide robust error handling and clear user feedback

It is intentionally written as an educational example for engineering students.
"""

# Configure structured logging instead of disabling it. In an educational setting,
# logs are useful to understand the flow and to debug issues. Adjust the level if needed.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

print("\n" + "="*50)
print("  Store Helper Chat - Type 'exit' to quit")
print("="*50 + "\n")

async def _read_input(prompt: str) -> str:
    """Read input in a way that doesn't block the event loop."""
    try:
        import asyncio
        return await asyncio.to_thread(input, prompt)
    except Exception:  # Fallback to direct input if to_thread is unavailable
        return input(prompt)


async def _process_turn(
    assistant: StoreAssistant,
    db,
    chat,
    messages: list,
    current_state: dict,
    user_input: str,
) -> None:
    """Process a single user-assistant exchange with persistence and error handling."""
    # Save user message
    user_message = await chat_service.add_message(
        db,
        chat_id=chat.id,
        content=user_input,
        sender=Sender.CLIENT,
    )

    # Add user message to conversation history
    messages.append({"role": "user", "content": user_input})

    # Get bot response using the same assistant instance
    response = await assistant.get_response_by_thread_id(chat.id, current_state)

    # Validate response structure defensively
    content = response.get("content") if isinstance(response, dict) else None
    intent_value = response.get("intent") if isinstance(response, dict) else Intent.OTHER
    if not isinstance(content, str) or not content:
        content = "I couldn't generate a response. Please try again or rephrase your question."
        logger.warning("Assistant returned empty or invalid content: %s", response)

    try:
        # Try to coerce the model-provided intent to our Enum (by value)
        intent_enum = intent_value if isinstance(intent_value, Intent) else Intent(intent_value)
    except Exception:
        # If casting fails, default to OTHER
        intent_enum = Intent.OTHER

    print("\nBot:", content)

    # Add assistant's response to conversation history
    messages.append({"role": "assistant", "content": content})

    # Save bot response and update user's message intent
    await chat_service.add_message(
        db,
        chat_id=chat.id,
        content=content,
        sender=Sender.BOT,
        intent=intent_enum,
    )
    await message_service.update_message_intent(
        db,
        message_id=user_message.id,
        new_intent=intent_enum,
    )

    # Commit after each exchange
    await db.commit()


async def main() -> None:
    """Entry point: creates a chat session and runs a console REPL against the assistant."""
    # Get a new async session from our silent session factory
    async with get_db_session() as db:
        # Create a new chat
        chat = await chat_service.create(
            db,
            obj_in=ChatCreate()
        )
        # Initialize the assistant once
        assistant = StoreAssistant(db=db)
        # Initialize messages with system message
        messages = []
        current_state = {
            "chat_id": str(chat.id),
            "messages": messages,
            "name": "",
            "email": "",
            "last_inquiry_id": None
        }
        try:
            while True:
                try:
                    user_input = await _read_input("You: ")
                    if user_input is None:
                        print("\nNo input detected. Type 'exit' to quit.")
                        continue
                    if user_input.strip().lower() in ["quit", "exit", "q"]:
                        print(f"\nGoodbye! Your chat ID is: {chat.id}")
                        break

                    # Empty message guard
                    if not user_input.strip():
                        print("(Tip) You sent an empty message. Please type your question.")
                        continue

                    await _process_turn(assistant, db, chat, messages, current_state, user_input)

                except KeyboardInterrupt:
                    print(f"\nInterrupted. Your chat ID is: {chat.id}")
                    break
                except Exception as e:
                    logger.exception("An error occurred during the chat loop")
                    print(f"\nAn error occurred: {str(e)}\n")
                    try:
                        await db.rollback()
                    except Exception:
                        logger.error("Failed to rollback the transaction after an error.")
                    
        finally:
            await db.close()

if __name__ == "__main__":
    # Disable warnings before running
    import warnings
    warnings.filterwarnings("ignore")
    
    # Run the main function
    import asyncio
    asyncio.run(main())