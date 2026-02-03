"""
LangGraph agent definition.

Creates the agent graph for RAG-based question answering.
"""

from typing import Any

from langgraph.graph import END, StateGraph

from src.agent.nodes import detect_language, generate, retrieve
from src.agent.nodes.guardrail import guardrail
from src.agent.nodes.refusal import generate_refusal
from src.agent.state import AgentState
from src.config.logging import get_logger
from src.db.connection import get_db
from src.db.repositories.session import SessionRepository

logger = get_logger("agent")


def create_agent_graph() -> StateGraph:
    """
    Create the LangGraph agent graph.

    The graph follows this flow:
    1. detect_language - Detect user's language (EN/FR)
    2. retrieve - Get relevant context from vector store
    3. generate - Generate response using LLM

    Returns:
        Compiled StateGraph
    """
    # Create the graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("detect_language", detect_language)
    graph.add_node("guardrail", guardrail)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.add_node("refusal", generate_refusal)

    # Define edges
    graph.add_edge("detect_language", "guardrail")

    # Conditional edge from guardrail
    def route_guardrail(state: AgentState) -> str:
        """Route based on guardrail check."""
        if state.metadata.get("is_off_topic", False):
            return "refusal"
        return "retrieve"

    graph.add_conditional_edges(
        "guardrail",
        route_guardrail,
        {
            "refusal": "refusal",
            "retrieve": "retrieve"
        }
    )

    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    graph.add_edge("refusal", END)

    # Set entry point
    graph.set_entry_point("detect_language")

    return graph.compile()


class AgentExecutor:
    """
    High-level executor for the RAG agent.

    Handles session management and provides a clean interface for chat.
    """

    def __init__(self):
        """Initialize the agent executor."""
        self.graph = create_agent_graph()

    async def chat(
        self,
        message: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Process a chat message.

        Args:
            message: User message
            session_id: Optional session ID for conversation continuity

        Returns:
            Dict with response, sources, session_id, and metadata
        """
        logger.info(f"Processing chat: {message[:50]}...")

        # Get or create session
        async with get_db() as db:
            session_repo = SessionRepository(db)
            session, was_created = await session_repo.get_or_create_session(
                session_id=session_id,
                language="en",  # Will be updated after detection
            )
            current_session_id = session.id

            # Get conversation history
            history = await session_repo.get_conversation_history(
                current_session_id,
                max_messages=10,
            )

        # Create initial state
        initial_state = AgentState(
            query=message,
            session_id=current_session_id,
            conversation_history=history,
        )

        # Run the agent graph
        try:
            final_state = await self.graph.ainvoke(initial_state)
        except Exception as e:
            logger.error(f"Agent error: {e}")
            return {
                "response": "I encountered an error processing your request. Please try again.",
                "sources": [],
                "session_id": current_session_id,
                "language": "en",
                "error": str(e),
            }

        # LangGraph returns a dict, extract values
        # Handle both dict and AgentState object
        if isinstance(final_state, dict):
            response = final_state.get("response", "")
            sources = final_state.get("sources", [])
            language = final_state.get("language", "en")
            metadata = final_state.get("metadata", {})
        else:
            response = final_state.response
            sources = final_state.sources
            language = final_state.language
            metadata = final_state.metadata

        # Save messages to session
        async with get_db() as db:
            session_repo = SessionRepository(db)

            # Update session language
            await session_repo.update_language(
                current_session_id, language
            )

            # Save user message
            await session_repo.add_message(
                session_id=current_session_id,
                role="user",
                content=message,
            )

            # Save assistant response
            await session_repo.add_message(
                session_id=current_session_id,
                role="assistant",
                content=response,
                sources=sources,
            )

        return {
            "response": response,
            "sources": sources,
            "session_id": current_session_id,
            "language": language,
            "metadata": metadata,
        }


# Create singleton instance
_agent_executor: AgentExecutor | None = None


def get_agent() -> AgentExecutor:
    """Get or create the agent executor singleton."""
    global _agent_executor
    if _agent_executor is None:
        _agent_executor = AgentExecutor()
    return _agent_executor


def create_agent() -> AgentExecutor:
    """Create a new agent executor instance."""
    return AgentExecutor()
