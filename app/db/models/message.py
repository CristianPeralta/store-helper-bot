
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
    GENERAL_QUESTION = "general_question"
    GREETING = "greeting"
    STORE_INFO = "store_info"
    STORE_HOURS = "store_hours"
    STORE_CONTACT = "store_contact"
    STORE_PROMOTIONS = "store_promotions"
    STORE_PAYMENT_METHODS = "store_payment_methods"
    STORE_SOCIAL_MEDIA = "store_social_media"
    STORE_LOCATION = "store_location"
    PRODUCT_LIST = "product_list"
    PRODUCT_CATEGORIES = "product_categories"
    PRODUCT_DETAILS = "product_details"
    PRODUCT_LIST_BY_CATEGORY = "product_list_by_category"
    HUMAN_ASSISTANCE = "human_assistance"
    OTHER = "other"

class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id = Column(String, ForeignKey("chats.id"), nullable=False)
    content = Column(String, nullable=False)
    sender = Column(SQLEnum(Sender), nullable=False)
    intent = Column(SQLEnum(Intent), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chat = relationship("Chat", back_populates="messages")
