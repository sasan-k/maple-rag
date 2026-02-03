"""
Retriever node.

Retrieves relevant context from the vector store.
"""

from typing import Any

from src.agent.state import AgentState
from src.config.logging import get_logger
from src.config.settings import get_settings
from src.db.connection import get_db
from src.db.repositories.document import DocumentRepository
from src.llm.factory import EmbeddingFactory

logger = get_logger("agent.retriever")


async def retrieve(state: AgentState) -> AgentState:
    """
    Agent node: Retrieve relevant context from the vector store.

    Args:
        state: Current agent state with query

    Returns:
        Updated state with retrieved chunks and formatted context
    """
    settings = get_settings()
    query = state.query

    if not query:
        state.error = "No query provided"
        return state

    logger.info(f"Retrieving context for: {query[:50]}...")

    try:
        # Generate query embedding
        embeddings = EmbeddingFactory.create_embeddings()
        query_embedding = await embeddings.aembed_query(query)

        # Search vector store
        async with get_db() as db:
            doc_repo = DocumentRepository(db)

            # Search with optional language filter
            # For now, search all languages to get best results
            results = await doc_repo.similarity_search(
                embedding=query_embedding,
                k=settings.retrieval_top_k,
                language=None,  # Search all languages
            )

        # Process results
        chunks: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        for chunk, score in results:
            # Get chunk metadata
            metadata = chunk.metadata_ or {}
            url = metadata.get("url", "")
            title = metadata.get("title", "Unknown")

            # Skip if we already have content from this URL
            # (to avoid redundant context)
            if url in seen_urls and len(chunks) >= 3:
                continue
            seen_urls.add(url)

            chunks.append(
                {
                    "content": chunk.content,
                    "url": url,
                    "title": title,
                    "language": metadata.get("language", "en"),
                    "score": score,
                    "chunk_index": chunk.chunk_index,
                }
            )

            # Add as source
            state.add_source(
                title=title,
                url=url,
                snippet=chunk.content[:200] + "..."
                if len(chunk.content) > 200
                else chunk.content,
            )

        state.retrieved_chunks = chunks
        state.context = state.format_context()

        logger.info(f"Retrieved {len(chunks)} chunks")

        # Log retrieval quality
        if chunks:
            avg_score = sum(c["score"] for c in chunks) / len(chunks)
            state.metadata["retrieval_avg_score"] = avg_score
            state.metadata["retrieval_count"] = len(chunks)
            logger.debug(f"Average retrieval score: {avg_score:.3f}")

    except Exception as e:
        logger.error(f"Retrieval error: {e}")
        state.error = f"Failed to retrieve context: {e}"
        state.retrieved_chunks = []
        state.context = ""

    return state
