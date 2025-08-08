import os
import sys
import logging
from app.langchain.model import run_graph_once_with_interrupt
from app.services.chat import chat_service
from app.services.message import message_service
from app.db.models.message import Sender, Intent
from app.db.silent_session import get_db_session
from app.langchain.modelClass import StoreAssistant

# Disable all logging
logging.disable(logging.CRITICAL)

print("\n" + "="*50)
print("  Store Helper Chat - Type 'exit' to quit")
print("="*50 + "\n")

async def main():
    # Get a new async session from our silent session factory
    async with get_db_session() as db:
        # Create a new chat
        chat = await chat_service.create_chat(
            db,
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
                    user_input = input("You: ")
                    if user_input.lower() in ["quit", "exit", "q"]:
                        print("\nGoodbye! Your chat ID is:", chat.id)
                        break

                    # Save user message
                    user_message = await chat_service.add_message(
                        db,
                        chat_id=chat.id,
                        content=user_input,
                        sender=Sender.CLIENT
                    )

                    # Add user message to conversation history
                    messages.append({"role": "user", "content": user_input})
                    
                    # Get bot response using the same assistant instance
                    response = await assistant.get_response_by_thread_id(chat.id, current_state)
                    print("\nBot:", response["content"])
                    
                    # Add assistant's response to conversation history
                    messages.append({"role": "assistant", "content": response["content"]})
                    
                    # Save bot response
                    await chat_service.add_message(
                        db,
                        chat_id=chat.id,
                        content=response["content"],
                        sender=Sender.BOT,
                        intent=Intent(response["intent"])
                    )   
                    # Update intent of last message
                    await message_service.update_message_intent(
                        db,
                        message_id=user_message.id,
                        new_intent=Intent(response["intent"])
                    )
                    
                    # Commit after each exchange
                    await db.commit()
                    
                except Exception as e:
                    print(f"\nAn error occurred: {str(e)}\n")
                    await db.rollback()
                    
        finally:
            await db.close()

if __name__ == "__main__":
    # Disable warnings before running
    import warnings
    warnings.filterwarnings("ignore")
    
    # Run the main function
    import asyncio
    asyncio.run(main())