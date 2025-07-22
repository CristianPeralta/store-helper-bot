
from enum import Enum as PyEnum 
from sqlalchemy import Column, String, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base
import uuid

class Sender(PyEnum):
    CLIENT = "client"
    BOT = "bot"

class Intent(PyEnum):
    PRODUCT_INQUIRY = "product_inquiry"
    GENERAL_QUESTION = "general_question"

class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id = Column(String, ForeignKey("chats.id"), nullable=False)
    content = Column(String, nullable=False)
    sender = Column(SQLEnum(Sender), nullable=False)
    intent = Column(SQLEnum(Intent), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chat = relationship("Chat", back_populates="messages")
