
from enum import Enum as PyEnum 
from sqlalchemy import Column, String, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base
import uuid

class Sender(PyEnum):
    CLIENT = "CLIENT"
    BOT = "BOT"

class Intent(PyEnum):
    GENERAL_QUESTION = "GENERAL_QUESTION"
    GREETING = "GREETING"
    STORE_INFO = "STORE_INFO"
    STORE_HOURS = "STORE_HOURS"
    STORE_CONTACT = "STORE_CONTACT"
    STORE_PROMOTIONS = "STORE_PROMOTIONS"
    STORE_PAYMENT_METHODS = "STORE_PAYMENT_METHODS"
    STORE_SOCIAL_MEDIA = "STORE_SOCIAL_MEDIA"
    STORE_LOCATION = "STORE_LOCATION"
    PRODUCT_LIST = "PRODUCT_LIST"
    PRODUCT_CATEGORIES = "PRODUCT_CATEGORIES"
    PRODUCT_DETAILS = "PRODUCT_DETAILS"
    PRODUCT_LIST_BY_CATEGORY = "PRODUCT_LIST_BY_CATEGORY"
    HUMAN_ASSISTANCE = "HUMAN_ASSISTANCE"
    OTHER = "OTHER"

class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id = Column(String, ForeignKey("chats.id"), nullable=False)
    content = Column(String, nullable=False)
    sender = Column(SQLEnum(Sender), nullable=False)
    intent = Column(SQLEnum(Intent), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chat = relationship("Chat", back_populates="messages")
