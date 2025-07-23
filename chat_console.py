import os
import sys
import logging
from app.langchain.model import run_graph_once_with_interrupt
from app.services.chat import chat_service
from app.services.message import message_service
from app.db.models.message import Sender, Intent
from app.db.silent_session import get_db_session

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
            client_name="Console User",
            client_email="console@example.com"
        )
        
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
                    
                    # Get bot response
                    response = run_graph_once_with_interrupt(user_input)
                    print("\nBot:", response["content"], "\n")
                    
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