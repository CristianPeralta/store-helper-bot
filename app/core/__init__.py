"""
Core module containing essential configurations and utilities for the application.

This module provides:
- Application settings and configuration
- Logging configuration
"""

from .config import get_settings, Settings
from .logging import LoggerConfig, logger

__all__ = [
    'get_settings',
    'Settings',
    'LoggerConfig',
    'logger'
]
