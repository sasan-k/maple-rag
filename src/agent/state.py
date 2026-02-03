"""
Agent state definition.

Defines the state that flows through the LangGraph agent.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentState:
    """
    State for the RAG agent.

    This state flows through the agent graph nodes.
    """

    # User input
    query: str = ""
    session_id: str | None = None

    # Detected language
    language: str = "en"

    # Conversation history (for context)
    conversation_history: list[dict[str, str]] = field(default_factory=list)

    # Retrieved context
    retrieved_chunks: list[dict[str, Any]] = field(default_factory=list)
    context: str = ""

    # Agent response
    response: str = ""
    sources: list[dict[str, str]] = field(default_factory=list)

    # Metadata
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_source(self, title: str, url: str, snippet: str = "") -> None:
        """Add a source citation."""
        self.sources.append(
            {
                "title": title,
                "url": url,
                "snippet": snippet,
            }
        )

    def format_context(self) -> str:
        """Format retrieved chunks as context string."""
        if not self.retrieved_chunks:
            return ""

        context_parts = []
        for i, chunk in enumerate(self.retrieved_chunks, 1):
            title = chunk.get("title", "Unknown")
            url = chunk.get("url", "")
            content = chunk.get("content", "")
            context_parts.append(
                f"[Source {i}] {title}\nURL: {url}\nContent: {content}\n"
            )

        return "\n---\n".join(context_parts)

    def format_history(self) -> str:
        """Format conversation history as string."""
        if not self.conversation_history:
            return "No previous conversation."

        parts = []
        for msg in self.conversation_history[-6:]:  # Last 6 messages (3 exchanges)
            role = msg.get("role", "unknown").capitalize()
            content = msg.get("content", "")
            parts.append(f"{role}: {content}")

        return "\n".join(parts)
