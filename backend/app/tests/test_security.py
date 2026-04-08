"""Tests for PII detection and redaction."""

from app.core.security import detect_pii, redact_pii


def test_email_detection() -> None:
    """Test email detection."""
    text = "Contact me at john.doe@example.com or jane@test.org"
    pii = detect_pii(text)

    assert "emails" in pii
    assert len(pii["emails"]) == 2
    assert "john.doe@example.com" in pii["emails"]


def test_phone_detection() -> None:
    """Test phone number detection."""
    text = "Call me at 555-123-4567 or (555) 987-6543"
    pii = detect_pii(text)

    assert "phones" in pii
    assert len(pii["phones"]) >= 1


def test_email_redaction() -> None:
    """Test email redaction."""
    text = "My email is john@example.com"
    redacted = redact_pii(text)

    assert "john@example.com" not in redacted
    assert "[EMAIL]" in redacted


def test_phone_redaction() -> None:
    """Test phone redaction."""
    text = "Call 555-123-4567"
    redacted = redact_pii(text)

    assert "555-123-4567" not in redacted
    assert "[PHONE]" in redacted


def test_multiple_pii_redaction() -> None:
    """Test multiple PII types."""
    text = "Email me at john@example.com or call (555) 123-4567"
    redacted = redact_pii(text)

    assert "john@example.com" not in redacted
    assert "[EMAIL]" in redacted
    # Phone number should be redacted
    assert "[PHONE]" in redacted or "(555) 123-4567" not in redacted
