"""Logging configuration using structlog."""

import logging
import sys
from typing import Any

import structlog

from app.core.config import get_settings

settings = get_settings()


def sanitize_event_dict(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitize event dict to redact PII before logging.

    This processor runs before rendering and redacts sensitive information
    from all string values in the event dict.
    """
    # Import here to avoid circular dependency
    from app.core.security import redact_pii

    sanitized = {}
    for key, value in event_dict.items():
        if isinstance(value, str):
            sanitized[key] = redact_pii(value)
        elif isinstance(value, dict):
            sanitized[key] = {k: redact_pii(v) if isinstance(v, str) else v for k, v in value.items()}
        else:
            sanitized[key] = value

    return sanitized


def setup_logging() -> None:
    """Configure structured logging."""
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            sanitize_event_dict,  # Add PII sanitization processor
            structlog.processors.JSONRenderer() if not settings.is_development
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )


def get_logger(name: str) -> Any:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def redact_sensitive_data(data: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive information from log data."""
    sensitive_keys = {
        "password",
        "secret",
        "token",
        "api_key",
        "authorization",
        "cookie",
        "session",
    }

    redacted = {}
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            redacted[key] = "***REDACTED***"
        elif isinstance(value, dict):
            redacted[key] = redact_sensitive_data(value)
        else:
            redacted[key] = value

    return redacted
