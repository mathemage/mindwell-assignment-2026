"""Custom exceptions for the application."""

from typing import Any


class MindwellException(Exception):
    """Base exception for all Mindwell errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ConfigurationError(MindwellException):
    """Configuration error."""

    pass


class DatabaseError(MindwellException):
    """Database operation error."""

    pass


class AuthenticationError(MindwellException):
    """Authentication error."""

    pass


class AuthorizationError(MindwellException):
    """Authorization error."""

    pass


class ValidationError(MindwellException):
    """Validation error."""

    pass


class RAGError(MindwellException):
    """RAG pipeline error."""

    pass


class EmbeddingError(MindwellException):
    """Embedding generation error."""

    pass


class SafetyViolationError(MindwellException):
    """Safety policy violation."""

    def __init__(
        self,
        message: str,
        violation_type: str,
        severity: str = "high",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, details)
        self.violation_type = violation_type
        self.severity = severity


class LLMError(MindwellException):
    """LLM provider error."""

    pass


class DocumentProcessingError(MindwellException):
    """Document processing error."""

    pass
