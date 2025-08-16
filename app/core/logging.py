import logging
import sys
from pathlib import Path
from typing import Optional, Union

from .config import get_settings

settings = get_settings()

class LoggerConfig:
    """Centralized logging configuration."""
    
    @classmethod
    def setup_logger(
        cls,
        name: str = "app",
        log_level: Optional[Union[str, int]] = None,
        log_file: Optional[Union[str, Path]] = None,
        console: bool = True,
        propagate: bool = False
    ) -> logging.Logger:
        """
        Configure and return a logger instance.
        
        Args:
            name: Logger name (use __name__ for module-level loggers)
            log_level: Logging level as string ('DEBUG', 'INFO', etc.) or logging constant
            log_file: Optional file path to write logs to
            console: Whether to log to console
            propagate: Whether to propagate logs to parent loggers
            
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)
        
        # Don't add handlers if they're already configured
        if logger.handlers:
            return logger
            
        # Set log level
        if log_level is None:
            log_level = settings.LOG_LEVEL
        if isinstance(log_level, str):
            log_level = getattr(logging, log_level.upper(), logging.INFO)
        logger.setLevel(log_level)
        
        # Debug: Print the log level being set
        print(f"Setting log level for {name} to {logging.getLevelName(log_level)}")
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Add console handler
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        
        # Add file handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        # Control propagation
        logger.propagate = propagate
        
        return logger
    
    @classmethod
    def get_logger(
        cls,
        name: Optional[str] = None,
        level: Optional[Union[str, int]] = None
    ) -> logging.Logger:
        """Get a configured logger instance with default settings."""
        name = name or __name__.rsplit('.', 1)[0]
        return cls.setup_logger(name=name, log_level=level)

# Default application logger
logger = LoggerConfig.setup_logger("app")
