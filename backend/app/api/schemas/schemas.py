"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# Auth schemas
class LoginRequest(BaseModel):
    """Login request."""

    email: str = Field(..., description="User email")


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """User response."""

    id: str
    email: str
    pseudonym: str
    is_admin: bool
    created_at: datetime


# Chat schemas
class ChatRequest(BaseModel):
    """Chat request."""

    message: str = Field(..., description="User message", min_length=1)
    conversation_id: str | None = Field(None, description="Optional conversation ID")


class Citation(BaseModel):
    """Citation information."""

    document_id: str
    document_title: str
    section_heading: str
    chunk_index: int
    text_snippet: str


class ChatMessage(BaseModel):
    """Chat message."""

    id: str
    content: str
    citations: list[Citation]
    safety_outcome: str


class ChatResponse(BaseModel):
    """Chat response."""

    conversation_id: str
    message: ChatMessage


class ConversationListItem(BaseModel):
    """Conversation list item."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class MessageListItem(BaseModel):
    """Message list item."""

    id: str
    role: str
    content: str
    created_at: datetime
    metadata: dict[str, Any]


# Document schemas
class DocumentUploadResponse(BaseModel):
    """Document upload response."""

    id: str
    title: str
    source_type: str
    chunk_count: int
    created_at: datetime


class DocumentListItem(BaseModel):
    """Document list item."""

    id: str
    title: str
    source_type: str
    created_at: datetime
    updated_at: datetime


class DocumentResponse(BaseModel):
    """Document response."""

    id: str
    title: str
    source_type: str
    content: str
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ReindexResponse(BaseModel):
    """Reindex response."""

    document_id: str
    chunk_count: int
    message: str


# Error schemas
class ErrorResponse(BaseModel):
    """Error response."""

    detail: str
    code: str | None = None
