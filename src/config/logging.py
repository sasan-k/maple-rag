"""
Logging configuration with structured JSON output.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from src.config.settings import get_settings


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string."""
        log_obj: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request_id if present
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id

        # Add extra fields
        if hasattr(record, "extra"):
            log_obj["extra"] = record.extra

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


class SimpleFormatter(logging.Formatter):
    """Simple formatter for development."""

    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def setup_logging() -> logging.Logger:
    """
    Set up logging configuration.

    Returns JSON formatted logs in production, simple format in development.
    """
    settings = get_settings()

    # Create logger
    logger = logging.getLogger("canadaca")
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    # Use JSON formatter in production, simple in development
    if settings.is_production:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(SimpleFormatter())

    logger.addHandler(handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name, will be prefixed with 'canadaca.'

    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"canadaca.{name}")
    return logging.getLogger("canadaca")
