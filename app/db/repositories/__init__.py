"""
Database repositories for data access.

This package contains repository classes that abstract database operations,
providing a clean separation between database access and business logic.
"""

from .base import BaseRepository  # noqa

__all__ = ["BaseRepository"]
