import os
import re
from langchain.chat_models import init_chat_model
import json
from typing import Annotated, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph, START
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import ToolMessage
from app.services.store import StoreService

store_service = StoreService()

os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")
os.environ["FIREWORKS_API_KEY"] = os.getenv("FIREWORKS_API_KEY")

llm = init_chat_model("accounts/fireworks/models/qwen3-30b-a3b", model_provider="fireworks")
# llm = init_chat_model("gemini-2.0-flash", model_provider="google_genai")
class State(TypedDict):
    messages: Annotated[list, add_messages]

@tool
def human_assistance2(query: str) -> str:
    """Use this tool when you cannot answer the user's request and human input is needed."""
    print("\n=== INTERRUPCIÓN HUMANA REQUERIDA ===")
    print("Consulta del modelo:", query)
    human_response = interrupt({"query": query})
    print("Respuesta del humano:", human_response["data"])
    return human_response["data"]
    
@tool
def human_assistance(
    name: str,
    email: str,
    query: str,
    tool_call_id: Annotated[str, InjectedToolCallId]
) -> Command[Dict[str, Any]]:
    """
    Use this tool to register a user inquiry for human follow-up via email.

    If 'name' or 'email' are not yet known, the assistant should ask the user
    to provide them before calling this tool.

    Args:
        name: The name of the person making the inquiry
        email: The email where they can be contacted
        query: The question or request they have
        tool_call_id: Unique ID for this tool call
        
    Returns:
        Command to update the state with confirmation message
    """
    if not name or not email or not query:
        return Command(
            update={
                "messages": [
                    ToolMessage("Success", tool_call_id=tool_call_id),
                    ToolMessage("Please provide a name, email, and query.", tool_call_id=tool_call_id)
                ],
            }
        )
    # In a real implementation, you would store this in a database or queue
    # For now, we'll just print it and return a confirmation
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    inquiry_id = f"INQ-{int(time.time())}"
    
    inquiry_details = {
        "inquiry_id": inquiry_id,
        "timestamp": timestamp,
        "name": name.strip(),
        "email": email.strip(),
        "query": query.strip(),
        "status": "pending"
    }
    
    # Print for demonstration (in production, this would go to a database/queue)
    print("\n=== NEW INQUIRY REGISTERED ===")
    print(f"Inquiry ID: {inquiry_id}")
    print(f"Name: {name}")
    print(f"Email: {email}")
    print(f"Query: {query}")
    print(f"Status: pending\n")
    
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
                ToolMessage("Success", tool_call_id=tool_call_id),
                ToolMessage(response, tool_call_id=tool_call_id)
            ],
        }
    )

@tool
def get_store_data(intent: str, tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
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
        "store_info": store_service.get_store_info,
        "store_hours": store_service.get_store_hours,
        "store_contact": store_service.get_contact_info,
        "store_promotions": store_service.get_promotions,
        "store_payment_methods": store_service.get_payment_methods,
        "store_social_media": store_service.get_social_media_links,
        "store_location": store_service.get_location
    }

    if intent not in mapping:
        return Command(update={
            "messages": [
                ToolMessage(f"Intent '{intent}' is not supported.", tool_call_id=tool_call_id)
            ]
        })

    try:
        # Call the synchronous store service method directly
        result = mapping[intent]()
        
        # Handle Pydantic models by converting to dict
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
        return Command(update={
            "messages": [
                ToolMessage(f"Error fetching store data: {error_msg}", tool_call_id=tool_call_id)
            ]
        })


graph_builder = StateGraph(State)

tools = [human_assistance, get_store_data]

llm_with_tools = llm.bind_tools(tools)

def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}

graph_builder.add_edge(START, "chatbot")
graph_builder.add_node("chatbot", chatbot)


tool_node = ToolNode(tools=tools)
graph_builder.add_node("tools", tool_node)

# The `tools_condition` function returns "tools" if the chatbot asks to use a tool, and "END" if
# it is fine directly responding. This conditional routing defines the main agent loop.
graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)

graph_builder.add_edge("tools", "chatbot")


# graph_builder.set_entry_point("chatbot")
memory = InMemorySaver()
graph = graph_builder.compile(checkpointer=memory)

def run_graph_once_with_interrupt(thread_id: str = "1", current_state: State = None):
    system_message = {
        "role": "system",
        "content": (
            "You are an assistant that always responds in JSON format with the following fields:\n"
            "- `reply`: your natural language response to the user\n"
            "- `intent`: a single word identifying the user's intent\n\n"
            "You must classify the user's intent using **only one** of the following categories:\n"
            "- product_inquiry\n"
            "- general_question\n"
            "- greeting\n"
            "- store_info\n"
            "- store_hours\n"
            "- store_contact\n"
            "- store_promotions\n"
            "- store_payment_methods\n"
            "- store_social_media\n"
            "- store_location\n"
            "- other\n\n"
            "If the user asks for something you cannot answer, call the `human_assistance` tool\n"
            "If the user asks about the store, you may call the appropriate store info tool `get_store_data`.\n"
            "Always respond in this exact JSON format:\n"
            "{\"reply\": \"<your reply here>\", \"intent\": \"<one of the above categories>\"}\n\n"
            "Example:\n"
            "User: 'Hi there!'\n"
            "Response: {\"reply\": \"Hello! How can I assist you today?\", \"intent\": \"greeting\"}"
        )
    }
    current_state["messages"].append(system_message)
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(
        current_state,
        config=config,
    ) 
    # Normal result with messages
    if isinstance(result, dict) and "messages" in result:
        last_message = result["messages"][-1]
        content = last_message.content
        try:
            content = get_json_content(content)
            return {
                "content": content.get("reply", "No reply provided."),
                "intent": content.get("intent", "other")
            }
        except Exception as e:
            print("An error occurred:", e)
    return {
        "content": "No reply provided.",
        "intent": "other"
    }

def get_json_content(content: str) -> dict:
    print("\n=== CONTENIDO DEL MENSAJE ===")
    print(content)

    if not content or not content.strip():
        print("⚠️ ALERTA: contenido vacío")
        return {"reply": "Empty response", "intent": "other"}

    # Buscar todos los posibles bloques JSON, incluso si están dentro de ```json ... ```
    bloques = re.findall(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
    
    # Si no se encontró con ```json```, intentar buscar JSON suelto
    if not bloques:
        bloques = re.findall(r'\{.*?\}', content, re.DOTALL)

    # Probar del último al primero por si hay JSON malformados antes
    for bloque in reversed(bloques):
        try:
            parsed = json.loads(bloque)
            return parsed
        except json.JSONDecodeError:
            continue  # ignorar bloques malformados

    print("⚠️ No se encontró JSON válido.")
    return {"reply": "Invalid or missing JSON", "intent": "other"}