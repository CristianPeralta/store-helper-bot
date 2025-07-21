import logging
import sys
from pathlib import Path
from typing import Optional

from .config import get_settings

settings = get_settings()

class LoggerConfig:
    """Centralized logging configuration."""
    
    @staticmethod
    def setup_logger(
        name: str = "app",
        log_level: Optional[str] = None,
        log_file: Optional[Path] = None
    ) -> logging.Logger:
        """
        Configure and return a logger instance.
        
        Args:
            name: Logger name
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_file: Optional file to write logs to
            
        Returns:
            Configured logger instance
        """
        log_level = log_level or settings.LOG_LEVEL
        logger = logging.getLogger(name)
        logger.setLevel(log_level)
        
        # Clear existing handlers
        logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler if log file is specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger

# Default application logger
logger = LoggerConfig.setup_logger("app")
