from sqlalchemy import Column, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base
import uuid

class Sender(Enum):
    CLIENT = "client"
    BOT = "bot"

class Intent(Enum):
    PRODUCT_INQUIRY = "product_inquiry"
    GENERAL_QUESTION = "general_question"

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id = Column(String, ForeignKey("chats.id"), nullable=False)
    content = Column(String, nullable=False)
    sender = Column(Enum(Sender), nullable=False)
    intent = Column(Enum(Intent), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chat = relationship("Chat", back_populates="messages")
