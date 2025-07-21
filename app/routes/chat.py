from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()
class ChatRequest(BaseModel):
  session_id: str
  message: str

class ChatResponse(BaseModel):
  response: str
  intent: str

@router.post("/", response_model=ChatResponse)
def handle_chat(req: ChatRequest):
  return ChatResponse(
    response="Hello, I'm your assistant. How can I help you?",
    intent="greeting"
  )
