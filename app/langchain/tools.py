import time
import logging
from typing import Optional
from typing import Annotated, Dict, Any
from dotenv import load_dotenv
load_dotenv()
from langgraph.types import Command
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from app.services.store import StoreService
from app.services.product import ProductService
from app.services.chat import chat_service
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

class ToolManager:
    """Registers and exposes tool functions for the assistant."""
    def __init__(self, db: AsyncSession):
        self.db = db
        self.store_service = StoreService()
        self.product_service = ProductService()
        self.chat_service = chat_service
        self.tools = [
            self._create_human_assistance_tool(),
            self._create_store_data_tool(),
            self._create_products_data_tool()
        ]
    
    def _create_human_assistance_tool(self):
        @tool
        async def human_assistance(
            name: str,
            email: str,
            query: str,
            chat_id: str,
            tool_call_id: Annotated[str, InjectedToolCallId],
        ) -> Command[Dict[str, Any]]:
            """
            Use this tool to register a user inquiry for human follow-up via email.

            If 'name' or 'email' are not yet known, the assistant should ask the user
            to provide them before calling this tool.

            Args:
                name: The name of the person making the inquiry
                email: The email where they can be contacted
                query: The question or request they have
                chat_id: The chat_id for the current conversation
                tool_call_id: Unique ID for this tool call
            
            Returns:
                Command to update the state with confirmation message
            """
            logger.info("human_assistance tool called | chat_id=%s", chat_id)
            if not chat_id:
                return Command(
                    update={
                        "messages": [
                            ToolMessage("Sorry, now we can't register your inquiry. Please try again later.", tool_call_id=tool_call_id)
                        ],
                    }
                )

            if not name or not email or not query:
                return Command(
                    update={
                        "messages": [
                            ToolMessage("Please provide a name, email, and query.", tool_call_id=tool_call_id)
                        ],
                    }
                )
            inquiry_id = f"INQ-{int(time.time())}"
            
            try:
                await self.chat_service.transfer_to_operator(
                    db=self.db,
                    chat_id=chat_id,
                    client_name=name,
                    client_email=email,
                    query=query,
                    inquiry_id=inquiry_id
                )
            except Exception as e:
                logger.exception("Failed to save client info for transfer")
                return Command(
                    update={
                        "messages": [
                            ToolMessage("An error occurred while registering your inquiry, please try again later.", tool_call_id=tool_call_id)
                        ],
                    }
                )
            
            # Log for demonstration (in production, this would go to a database/queue)
            logger.info(
                "NEW INQUIRY REGISTERED | id=%s name=%s email=%s status=pending",
                inquiry_id, name, email,
            )
            
            # Prepare the response to the user
            response = (
                f"Thank you, {name}! Your inquiry has been registered (ID: {inquiry_id}). "
                f"A member of our team will contact you at {email} within 24-48 hours. "
                "Please include your inquiry ID in any follow-up communications."
            )
            
            # Return a command to update the state
            return Command(
                update={
                    "name": name,
                    "email": email,
                    "last_inquiry_id": inquiry_id,
                    "messages": [
                        ToolMessage(response, tool_call_id=tool_call_id)
                    ],
                }
            )
        return human_assistance

    def _create_store_data_tool(self):
        @tool
        async def get_store_data(intent: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
            """
            Fetch store-related information based on intent. Supported intents:
            - store_info
            - store_hours
            - store_contact
            - store_promotions
            - store_payment_methods
            - store_social_media
            - store_location
            """

            mapping = {
                "store_info": self.store_service.get_store_info,
                "store_hours": self.store_service.get_store_hours,
                "store_contact": self.store_service.get_contact_info,
                "store_promotions": self.store_service.get_promotions,
                "store_payment_methods": self.store_service.get_payment_methods,
                "store_social_media": self.store_service.get_social_media_links,
                "store_location": self.store_service.get_location
            }
            logger.info("get_store_data called | intent=%s", intent)
            if intent not in mapping:
                return Command(update={
                    "messages": [
                        ToolMessage(f"Intent '{intent}' is not supported.", tool_call_id=tool_call_id)
                    ]
                })

            try:
                logger.debug("Calling store service")
                # Call the synchronous store service method directly
                result = mapping[intent]()
                logger.debug("Store service returned successfully")
                
                # Handle Pydantic models by converting to dict
                if hasattr(result, 'model_dump'):
                    result = result.model_dump()
                elif hasattr(result, 'dict'):  # Fallback for older Pydantic versions
                    result = result.dict()
                
                # Format the response based on the result type
                if isinstance(result, dict):
                    # Flatten nested dictionaries for better readability
                    def flatten_dict(d, parent_key='', sep=' '):
                        items = []
                        for k, v in d.items():
                            new_key = f"{parent_key}{sep}{k}" if parent_key else k
                            if isinstance(v, dict):
                                items.extend(flatten_dict(v, new_key, sep).items())
                            else:
                                items.append((new_key, v))
                        return dict(items)
                    
                    flat_result = flatten_dict(result)
                    reply = "\n".join(f"- {k.replace('_', ' ').capitalize()}: {v}" for k, v in flat_result.items())
                elif isinstance(result, (list, tuple)):
                    reply = "\n".join(f"- {item}" for item in result)
                else:
                    reply = str(result)
                    
                return Command(update={
                    "messages": [
                        ToolMessage(reply, tool_call_id=tool_call_id)
                    ]
                })
                
            except Exception as e:
                error_msg = str(e)
                if hasattr(e, 'detail'):
                    error_msg = e.detail
                logger.exception("Error fetching store data: %s", error_msg)
                return Command(update={
                    "messages": [
                        ToolMessage(f"Error fetching store data: {error_msg}", tool_call_id=tool_call_id)
                    ]
                })
        return get_store_data

    def _create_products_data_tool(self):
        @tool
        async def get_products_data(intent: str, tool_call_id: Annotated[str, InjectedToolCallId], category: Optional[str] = None, product_id: Optional[int] = None) -> Command:
            """
            Fetch product-related information based on intent.

            Args:
                intent: The intent to fetch data for
                category: The category to filter by
                product_id: The ID of the product to retrieve
                tool_call_id: Unique ID for this tool call

            Supported intents:
            - product_list_by_category: List of products in a specific category by category name
            - product_categories: List of all product categories
            - product_details: Details of a specific product by product id
            - product_list: List of all products
            """

            # Define the mapping of intents to async functions
            mapping = {
                "product_list": self.product_service.get_products,
                "product_categories": self.product_service.get_categories,
                "product_details": self.product_service.get_product,
                "product_list_by_category": self.product_service.get_products_by_category
            }

            # Validate intent
            if intent not in mapping:
                return Command(update={
                    "messages": [
                        ToolMessage(f"Intent '{intent}' is not supported.", tool_call_id=tool_call_id)
                    ]
                })

            # Validate required parameters
            if intent == "product_list_by_category" and not category:
                return Command(update={
                    "messages": [
                        ToolMessage("Please provide a category.", tool_call_id=tool_call_id)
                    ]
                })
            
            if intent == "product_details" and not product_id:
                return Command(update={
                    "messages": [
                        ToolMessage("Please provide a product ID.", tool_call_id=tool_call_id)
                    ]
                })

            logger.info("get_products_data called | intent=%s", intent)

            try:
                # Call the appropriate async function with parameters
                if intent == "product_list_by_category":
                    result = await self.product_service.get_products_by_category(category)
                elif intent == "product_details":
                    result = await self.product_service.get_product(product_id)
                elif intent == "product_list":
                    result = await self.product_service.get_products()
                elif intent == "product_categories":
                    result = await self.product_service.get_categories()
                else:
                    result = await mapping[intent]()

                # Convert Pydantic models to dict if needed
                if hasattr(result, 'dict'):
                    result = result.dict()
                
                # Format the response based on the result type
                if isinstance(result, dict):
                    # Flatten nested dictionaries for better readability
                    def flatten_dict(d, parent_key='', sep=' '):
                        items = []
                        for k, v in d.items():
                            new_key = f"{parent_key}{sep}{k}" if parent_key else k
                            if isinstance(v, dict):
                                items.extend(flatten_dict(v, new_key, sep).items())
                            else:
                                items.append((new_key, v))
                        return dict(items)
                    
                    flat_result = flatten_dict(result)
                    reply = "\n".join(f"- {k.replace('_', ' ').capitalize()}: {v}" for k, v in flat_result.items())
                elif isinstance(result, (list, tuple)):
                    reply = "\n".join(f"- {item}" for item in result)
                else:
                    reply = str(result)
                    
                return Command(update={
                    "messages": [
                        ToolMessage(reply, tool_call_id=tool_call_id)
                    ]
                })
                
            except Exception as e:
                error_msg = str(e)
                if hasattr(e, 'detail'):
                    error_msg = e.detail
                logger.exception("get_products_data failed: %s", error_msg)
                return Command(update={
                    "messages": [
                        ToolMessage(f"Error fetching product data: {error_msg}", tool_call_id=tool_call_id)
                    ]
                })
        return get_products_data
