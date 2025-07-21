"""
Database module.

This module provides database configuration, session management, and base classes
for models and repositories.
"""
from .base import Base, database
from .session import get_db, get_db_session
from .repositories import BaseRepository

# Import models to ensure they are registered with SQLAlchemy
# This must be after Base is defined
from .models.chat import Chat  # noqa
from .models.message import Message  # noqa

__all__ = [
    'Base',
    'database',
    'get_db',
    'get_db_session',
    'BaseRepository',
    # Models
    'Chat',
    'Message',
]
