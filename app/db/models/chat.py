from enum import Enum as PyEnum 
from sqlalchemy import Column, String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base
import uuid

class Intent(PyEnum):
    GENERAL_QUESTION = "GENERAL_QUESTION"
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

class Chat(Base):
    __tablename__ = "chats"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_name = Column(String, nullable=True)
    client_email = Column(String, nullable=True)
    initial_intent = Column(SQLEnum(Intent), nullable=True)
    transfer_inquiry_id = Column(String, nullable=True)
    transfer_query = Column(String, nullable=True)
    transferred_to_operator = Column(Boolean, default=False)
    operator_transfer_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")
