"""
Pydantic schemas for API requests and responses.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ============
# Chat Schemas
# ============


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User message to the chat agent",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional session ID for conversation continuity",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "How do I file my taxes?",
                    "session_id": None,
                }
            ]
        }
    }


class Source(BaseModel):
    """A source citation."""

    title: str = Field(..., description="Title of the source page")
    url: str = Field(..., description="URL of the source page")
    snippet: str = Field(default="", description="Relevant snippet from the source")


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""

    response: str = Field(..., description="Agent's response message")
    sources: list[Source] = Field(default_factory=list, description="Source citations")
    session_id: str = Field(..., description="Session ID for conversation continuity")
    language: str = Field(default="en", description="Detected language (en or fr)")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "response": "To file your taxes in Canada, you can...",
                    "sources": [
                        {
                            "title": "Filing your tax return",
                            "url": "https://www.canada.ca/en/...",
                            "snippet": "Learn how to file...",
                        }
                    ],
                    "session_id": "abc123",
                    "language": "en",
                }
            ]
        }
    }


# ============
# Session Schemas
# ============


class MessageSchema(BaseModel):
    """A chat message."""

    id: str
    role: str = Field(..., description="'user' or 'assistant'")
    content: str
    sources: list[Source] = Field(default_factory=list)
    created_at: datetime


class SessionResponse(BaseModel):
    """Response with session details and history."""

    session_id: str
    language: str
    messages: list[MessageSchema]
    created_at: datetime


# ============
# Health Schemas
# ============


class HealthCheck(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str = "0.1.0"


class ReadinessCheck(BaseModel):
    """Readiness check response."""

    status: str
    checks: dict[str, str]


# ============
# Admin Schemas
# ============


class IngestionRequest(BaseModel):
    """Request to ingest URLs."""

    urls: list[str] = Field(..., min_length=1, description="URLs to ingest")


class IngestionResponse(BaseModel):
    """Response from ingestion."""

    success: bool
    message: str
    stats: dict[str, Any] = Field(default_factory=dict)


class StatsResponse(BaseModel):
    """System statistics response."""

    documents: int
    chunks: int
    sessions: int | None = None
    last_updated: str | None = None
