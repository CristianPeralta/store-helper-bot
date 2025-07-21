from sqlalchemy import Column, Integer, JSON, ForeignKey
from app.db import Base

class ChatState(Base):
    __tablename__ = "chat_state"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), unique=True)
    state = Column(JSON)
