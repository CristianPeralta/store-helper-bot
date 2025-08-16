import os
import re
import json
import logging
from typing import Optional, Annotated, Dict, Any
from dotenv import load_dotenv
load_dotenv()

from langchain.chat_models import init_chat_model
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langgraph.types import Command
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START
from langgraph.prebuilt import ToolNode, tools_condition
from sqlalchemy.ext.asyncio import AsyncSession

from .tools import ToolManager

logger = logging.getLogger(__name__)

os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")
os.environ["FIREWORKS_API_KEY"] = os.getenv("FIREWORKS_API_KEY")

class State(TypedDict):
    messages: Annotated[list, add_messages]
    chat_id: str
    name: str
    email: str
    last_inquiry_id: Optional[str]

class StoreAssistant:
    """Assistant that orchestrates LLM + tools through a LangGraph."""
    def __init__(self, db: AsyncSession):
        self.tools = ToolManager(db=db).tools
        self.llm = self._get_llm_chat_model()
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.graph: StateGraph = self._build_graph()
        self.system_message: Optional[Dict[str, Any]] = None

    def _get_llm_chat_model(self):
        model_provider = os.getenv("MODEL_PROVIDER", "fireworks")
        logger.info("===> Using model provider: %s", model_provider)
        if model_provider == "fireworks":
            return init_chat_model(
                "accounts/fireworks/models/qwen3-30b-a3b",
                model_provider="fireworks"
            )
        elif model_provider == "openai":
            return init_chat_model(
                "qwen3:8b-q4_K_M",
                model_provider="openai",
                api_key="llm",
                base_url="http://localhost:11434/v1"
            )
        else:
            raise ValueError("Invalid MODEL_PROVIDER")
        
    def _get_system_message(self, chat_id: str) -> Dict[str, Any]:
        return {
            "role": "system",
            "content": (
                "You are an assistant that always responds in JSON format with the following fields:\n"
                "- `reply`: your natural language response to the user\n"
                "- `intent`: a single word identifying the user's intent\n\n"
                "You must classify the user's intent using **only one** of the following categories:\n"
                "- GENERAL_QUESTION\n"
                "- GREETING\n"
                "- STORE_INFO\n"
                "- STORE_HOURS\n"
                "- STORE_CONTACT\n"
                "- STORE_PROMOTIONS\n"
                "- STORE_PAYMENT_METHODS\n"
                "- STORE_SOCIAL_MEDIA\n"
                "- STORE_LOCATION\n"
                "- PRODUCT_LIST\n"
                "- PRODUCT_CATEGORIES\n"
                "- PRODUCT_DETAILS\n"
                "- PRODUCT_LIST_BY_CATEGORY\n"
                "- HUMAN_ASSISTANCE\n"
                "- OTHER\n\n"
                "If the user asks for something you cannot answer, call the `human_assistance` tool\n"
                f"In the case of human assistance, the chat_id parameter will be {chat_id}\n"
                "If the user asks about the store, you may call the appropriate store info tool `get_store_data`.\n"
                "If the user asks about the products, you may call the appropriate product info tool `get_products_data`.\n"
                "Always respond in this exact JSON format:\n"
                "{\"reply\": \"<your reply here>\", \"intent\": \"<one of the above categories>\"}\n\n"
                "Example:\n"
                "User: 'Hi there!'\n"
                "Response: {\"reply\": \"Hello! How can I assist you today?\", \"intent\": \"GREETING\"}"
            )
        }
        
    async def chatbot(self, state: State) -> Command:
        response = await self.llm_with_tools.ainvoke(state["messages"])
        return {"messages": [response]}

    def _build_graph(self) -> StateGraph:
        graph_builder = StateGraph(State)
        graph_builder.add_edge(START, "chatbot")
        graph_builder.add_node("chatbot", self.chatbot)
        tool_node = ToolNode(tools=self.tools)
        graph_builder.add_node("tools", tool_node)
        graph_builder.add_conditional_edges("chatbot", tools_condition)
        graph_builder.add_edge("tools", "chatbot")
        memory = InMemorySaver()
        graph = graph_builder.compile(checkpointer=memory)
        return graph

    def _parse_response(self, content: str) -> Dict[str, Any]:
        try:
            content = self.get_json_content(content)
            return {
                "content": content.get("reply", "No reply provided."),
                "intent": content.get("intent", "OTHER")
            }
        except Exception as e:
            logger.exception("Failed to parse model JSON response")
            return {
                "content": "No reply provided.",
                "intent": "OTHER"
            }
    
    def get_json_content(self, content: str) -> dict:
        logger.info("LLM raw content: %s", content)

        if not content or not content.strip():
            logger.warning("Empty content returned by the LLM")
            return {"reply": "Empty response", "intent": "OTHER"}

        # Search for all possible JSON blocks, even if they are inside 
        bloques = re.findall(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
    
        # If no ```json``` was found, try to find JSON on its own
        if not bloques:
            bloques = re.findall(r'\{.*?\}', content, re.DOTALL)

        # Try the last block first in case there are malformed JSONs before
        for bloque in reversed(bloques):
            try:
                parsed = json.loads(bloque)
                return parsed
            except json.JSONDecodeError:
                continue  # ignore malformed blocks

        logger.warning("No valid JSON found in LLM output")
        return {"reply": "Invalid or missing JSON", "intent": "OTHER"}
    
    async def _ensure_system_message(self, state: State, chat_id: str) -> None:
        """
        Ensure the system message is properly set in the state's messages.
        
        Args:
            state: The current chat state
            chat_id: The chat ID to use for getting system message
        """
        try:
            # Only set system message if not already set or if messages list is empty
            if not self.system_message or not state.get("messages") or \
            (state["messages"] and state["messages"][0] != self.system_message):
                self.system_message = self._get_system_message(chat_id=chat_id)
                if state.get("messages"):
                    state["messages"].insert(0, self.system_message)
                else:
                    state["messages"] = [self.system_message]
        except Exception as e:
            logger.exception("Error setting system message")
            raise
    
    async def get_response_by_thread_id(self, thread_id: str = "1", state: State = None) -> Dict[str, Any]:
        state = state or State(messages=[])
        
        config = {"configurable": {"thread_id": thread_id}}

        if not state.get("chat_id") and hasattr(self, 'chat_id'):
            state["chat_id"] = thread_id

        try:
            await self._ensure_system_message(state, thread_id)
        except KeyError as e:
            logger.exception("Failed to set system message")
            return {
                "content": "Error initializing chat. Please try again.",
                "intent": "OTHER",
                "state": state
            }

        try:
            result = await self.graph.ainvoke(state, config=config)
            if isinstance(result, dict) and "messages" in result:
                last_message = result["messages"][-1]
                content = last_message.content
                try:
                    content = self.get_json_content(content)
                    return {
                        "content": content.get("reply", "No reply provided."),
                        "intent": content.get("intent", "OTHER"),
                        "state": state
                    }
                except Exception as e:
                    logger.exception("Failed to extract JSON content from model reply")
                    return {"content": "No reply provided.", "intent": "OTHER", "state": state}
            else:
                logger.warning("No messages found in LangGraph result")
                return {"content": "No reply provided.", "intent": "OTHER", "state": state}
        except Exception as e:
            logger.exception("LangGraph invocation failed")
            return {"content": "No reply provided.", "intent": "OTHER", "state": state}


assistant = StoreAssistant