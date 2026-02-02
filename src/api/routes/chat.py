"""
Chat endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.graph import get_agent
from src.api.schemas import (
    ChatRequest,
    ChatResponse,
    MessageSchema,
    SessionResponse,
    Source,
)
from src.config.logging import get_logger
from src.db.connection import get_db_session
from src.db.repositories.session import SessionRepository

logger = get_logger("api.chat")

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "",
    response_model=ChatResponse,
    summary="Send a chat message",
    description="Send a message to the chat agent and receive a response with sources",
)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a chat message.

    The agent will:
    1. Detect the language (English or French)
    2. Search for relevant information from canada.ca
    3. Generate a response with citations

    If a session_id is provided, the conversation context will be maintained.
    """
    logger.info(f"Chat request: {request.message[:50]}...")

    try:
        agent = get_agent()
        result = await agent.chat(
            message=request.message,
            session_id=request.session_id,
        )

        return ChatResponse(
            response=result["response"],
            sources=[
                Source(
                    title=s.get("title", ""),
                    url=s.get("url", ""),
                    snippet=s.get("snippet", ""),
                )
                for s in result.get("sources", [])
            ],
            session_id=result["session_id"],
            language=result.get("language", "en"),
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing your request",
        )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    summary="Get session history",
    description="Retrieve the conversation history for a session",
)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> SessionResponse:
    """Get conversation history for a session."""
    session_repo = SessionRepository(db)

    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = await session_repo.get_messages(session_id)

    return SessionResponse(
        session_id=session.id,
        language=session.language,
        messages=[
            MessageSchema(
                id=m.id,
                role=m.role,
                content=m.content,
                sources=[
                    Source(
                        title=s.get("title", ""),
                        url=s.get("url", ""),
                        snippet=s.get("snippet", ""),
                    )
                    for s in m.sources or []
                ],
                created_at=m.created_at,
            )
            for m in messages
        ],
        created_at=session.created_at,
    )


@router.delete(
    "/sessions/{session_id}",
    summary="Delete a session",
    description="Delete a session and all its messages",
)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Delete a session."""
    session_repo = SessionRepository(db)

    deleted = await session_repo.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"status": "deleted", "session_id": session_id}
