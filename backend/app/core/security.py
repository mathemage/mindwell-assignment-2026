"""Security utilities for PII detection and redaction."""

import re
from typing import Any

from app.core.config import get_settings

settings = get_settings()

# PII detection patterns
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CREDIT_CARD_PATTERN = re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b")


def detect_pii(text: str) -> dict[str, list[str]]:
    """
    Detect PII in text.

    Args:
        text: Text to scan for PII

    Returns:
        Dictionary with detected PII types and values
    """
    detected: dict[str, list[str]] = {}

    emails = EMAIL_PATTERN.findall(text)
    if emails:
        detected["emails"] = emails

    phones = PHONE_PATTERN.findall(text)
    if phones:
        detected["phones"] = phones

    ssns = SSN_PATTERN.findall(text)
    if ssns:
        detected["ssns"] = ssns

    credit_cards = CREDIT_CARD_PATTERN.findall(text)
    if credit_cards:
        detected["credit_cards"] = credit_cards

    return detected


def redact_pii(text: str) -> str:
    """
    Redact PII from text.

    Args:
        text: Text to redact

    Returns:
        Text with PII redacted
    """
    if not settings.redact_pii:
        return text

    # Redact emails
    text = EMAIL_PATTERN.sub("[EMAIL]", text)

    # Redact phone numbers
    text = PHONE_PATTERN.sub("[PHONE]", text)

    # Redact SSNs
    text = SSN_PATTERN.sub("[SSN]", text)

    # Redact credit cards
    text = CREDIT_CARD_PATTERN.sub("[CREDIT_CARD]", text)

    return text


def sanitize_log_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Sanitize data for logging by redacting PII.

    Args:
        data: Data to sanitize

    Returns:
        Sanitized data
    """
    if not settings.redact_pii:
        return data

    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = redact_pii(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        elif isinstance(value, list):
            sanitized[key] = [redact_pii(item) if isinstance(item, str) else item for item in value]
        else:
            sanitized[key] = value

    return sanitized
