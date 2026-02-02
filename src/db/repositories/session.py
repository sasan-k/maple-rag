"""
Session repository for managing chat sessions and messages.
"""

import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import ChatMessage, ChatSession


class SessionRepository:
    """Repository for chat session operations."""

    def __init__(self, session: AsyncSession):
        """Initialize with a database session."""
        self.session = session

    @staticmethod
    def generate_id() -> str:
        """Generate a unique session ID."""
        return str(uuid.uuid4())

    async def create_session(
        self,
        language: str = "en",
        metadata: dict[str, Any] | None = None,
    ) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(
            id=self.generate_id(),
            language=language,
            metadata_=metadata or {},
        )
        self.session.add(session)
        await self.session.flush()
        return session

    async def get_session(self, session_id: str) -> ChatSession | None:
        """Get a session by ID."""
        result = await self.session.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_session(
        self,
        session_id: str | None,
        language: str = "en",
    ) -> tuple[ChatSession, bool]:
        """
        Get an existing session or create a new one.

        Args:
            session_id: Optional existing session ID
            language: Language for new sessions

        Returns:
            Tuple of (session, was_created)
        """
        if session_id:
            existing = await self.get_session(session_id)
            if existing:
                return existing, False

        # Create new session
        new_session = await self.create_session(language=language)
        return new_session, True

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages."""
        result = await self.session.execute(
            delete(ChatSession).where(ChatSession.id == session_id)
        )
        return result.rowcount > 0

    async def update_language(
        self, session_id: str, language: str
    ) -> ChatSession | None:
        """Update the language preference for a session."""
        chat_session = await self.get_session(session_id)
        if chat_session:
            chat_session.language = language
            await self.session.flush()
        return chat_session

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        sources: list[dict[str, Any]] | None = None,
    ) -> ChatMessage:
        """
        Add a message to a session.

        Args:
            session_id: The session ID
            role: 'user' or 'assistant'
            content: Message content
            sources: Optional list of source citations
        """
        message = ChatMessage(
            id=self.generate_id(),
            session_id=session_id,
            role=role,
            content=content,
            sources=sources or [],
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def get_messages(
        self,
        session_id: str,
        limit: int | None = None,
    ) -> list[ChatMessage]:
        """
        Get messages for a session.

        Args:
            session_id: The session ID
            limit: Optional limit on number of messages

        Returns:
            List of messages ordered by creation time
        """
        query = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )

        if limit:
            query = query.limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_recent_messages(
        self,
        session_id: str,
        count: int = 10,
    ) -> list[ChatMessage]:
        """
        Get the most recent messages for a session.

        Args:
            session_id: The session ID
            count: Number of recent messages to retrieve

        Returns:
            List of messages ordered by creation time (oldest first)
        """
        # Get last N messages ordered by created_at desc, then reverse
        query = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(count)
        )

        result = await self.session.execute(query)
        messages = list(result.scalars().all())
        messages.reverse()  # Return in chronological order
        return messages

    async def get_conversation_history(
        self,
        session_id: str,
        max_messages: int = 10,
    ) -> list[dict[str, str]]:
        """
        Get conversation history formatted for LLM context.

        Args:
            session_id: The session ID
            max_messages: Maximum number of messages to include

        Returns:
            List of {"role": "...", "content": "..."} dicts
        """
        messages = await self.get_recent_messages(session_id, max_messages)
        return [{"role": m.role, "content": m.content} for m in messages]

    async def clear_messages(self, session_id: str) -> int:
        """Clear all messages from a session."""
        result = await self.session.execute(
            delete(ChatMessage).where(ChatMessage.session_id == session_id)
        )
        return result.rowcount
