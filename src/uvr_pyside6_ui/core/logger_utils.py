"""
Logging utilities for UVR PySide6 UI.
Provides centralized logging configuration that can be easily controlled.
"""

import logging
import os
from typing import Optional

# Define log level constants directly to avoid circular imports
DEFAULT_LOG_LEVEL = "INFO"
DEBUG_LOG_LEVEL = "DEBUG"
LOG_FORMAT = "%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class UVRLogger:
    """Centralized logger for UVR application."""

    _loggers = {}
    _configured = False

    @classmethod
    def configure_logging(
        cls, log_level: Optional[str] = None, enable_console: bool = True
    ) -> None:
        """Configure logging for the entire application."""
        if cls._configured:
            return

        # Determine log level from environment variable or default
        if log_level is None:
            log_level = os.environ.get("UVR_LOG_LEVEL", DEFAULT_LOG_LEVEL)

        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format=LOG_FORMAT,
            datefmt=LOG_DATE_FORMAT,
            force=True,  # Override any existing configuration
        )

        # Disable logging for production if needed
        if not enable_console and log_level != DEBUG_LOG_LEVEL:
            logging.disable(logging.CRITICAL)

        cls._configured = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get a logger instance for the given name."""
        if not cls._configured:
            cls.configure_logging()

        if name not in cls._loggers:
            logger = logging.getLogger(f"uvr.{name}")
            cls._loggers[name] = logger

        return cls._loggers[name]

    @classmethod
    def set_level(cls, level: str) -> None:
        """Change the logging level for all UVR loggers."""
        log_level = getattr(logging, level.upper(), logging.INFO)
        for logger in cls._loggers.values():
            logger.setLevel(log_level)

        # Also update root logger
        logging.getLogger().setLevel(log_level)

    @classmethod
    def disable_logging(cls) -> None:
        """Disable all logging output."""
        logging.disable(logging.CRITICAL)

    @classmethod
    def enable_logging(cls) -> None:
        """Re-enable logging output."""
        logging.disable(logging.NOTSET)


def get_logger(name: str) -> logging.Logger:
    """Convenience function to get a logger."""
    return UVRLogger.get_logger(name)
