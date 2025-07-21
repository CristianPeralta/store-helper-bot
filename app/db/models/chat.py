from enum import Enum as PyEnum 
from sqlalchemy import Column, String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base
import uuid

class Intent(PyEnum):
    PRODUCT_INQUIRY = "product_inquiry"
    GENERAL_QUESTION = "general_question"

class Chat(Base):
    __tablename__ = "chats"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_name = Column(String, nullable=True)
    client_email = Column(String, nullable=True)
    initial_intent = Column(SQLEnum(Intent), nullable=True)
    transferred_to_operator = Column(Boolean, default=False)
    operator_transfer_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
