"""
SQLAlchemy models for the Canada.ca Chat Agent.
"""

from datetime import datetime, timezone
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Define types that fall back to generic types for non-Postgres (e.g. SQLite tests)
JSONVal = JSON().with_variant(JSONB, "postgresql")
VectorVal = String().with_variant(Vector(1024), "postgresql")


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


def utcnow() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


class Document(Base):
    """
    Represents a scraped document from canada.ca.

    Stores the full content and metadata of each page.
    """

    __tablename__ = "documents"
    __table_args__ = {"schema": "canadaca"}

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(String(512))
    content: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(2), default="en")

    # Incremental scraping fields
    sitemap_lastmod: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # Last modified date from sitemap XML
    last_scraped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # When we last scraped this page
    scrape_status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # 'pending', 'scraped', 'failed', 'changed', 'deleted'
    embedding_version: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # Track which embedding model was used

    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONVal, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    # Relationships
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, url={self.url[:50]}...)>"


class DocumentChunk(Base):
    """
    A chunk of a document with its vector embedding.

    Documents are split into chunks for efficient retrieval.
    """

    __tablename__ = "document_chunks"
    __table_args__ = (
        Index(
            "idx_document_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        {"schema": "canadaca"},
    )

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("canadaca.documents.id", ondelete="CASCADE")
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = Column(VectorVal)  # amazon.titan-embed-text-v2:0
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONVal, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<DocumentChunk(id={self.id}, doc={self.document_id}, idx={self.chunk_index})>"


class ChatSession(Base):
    """
    A chat session for maintaining conversation context.

    Sessions track conversation history and user preferences.
    """

    __tablename__ = "chat_sessions"
    __table_args__ = {"schema": "canadaca"}

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    language: Mapped[str] = mapped_column(String(2), default="en")
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONVal, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    last_activity: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    # Relationships
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, lang={self.language})>"


class ChatMessage(Base):
    """
    A message in a chat session.

    Stores both user and assistant messages with source citations.
    """

    __tablename__ = "chat_messages"
    __table_args__ = {"schema": "canadaca"}

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("canadaca.chat_sessions.id", ondelete="CASCADE"),
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user, assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONVal, default=list
    )  # Citation info
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    # Relationships
    session: Mapped["ChatSession"] = relationship(
        "ChatSession", back_populates="messages"
    )

    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, role={self.role})>"
