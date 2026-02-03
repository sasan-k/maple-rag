"""
Admin endpoints for system management.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import IngestionRequest, IngestionResponse, StatsResponse
from src.config.logging import get_logger
from src.db.connection import get_db_session
from src.db.repositories.document import DocumentRepository
from src.scraper.ingestion import CANADA_TAX_URLS, IngestionPipeline

logger = get_logger("api.admin")

router = APIRouter(prefix="/admin", tags=["admin"])


async def run_ingestion(urls: list[str]) -> None:
    """Background task to run ingestion."""
    logger.info(f"Starting background ingestion of {len(urls)} URLs")
    pipeline = IngestionPipeline(urls=urls)
    stats = await pipeline.run()
    logger.info(
        f"Ingestion complete: {stats.successful} successful, "
        f"{stats.failed} failed, {stats.total_chunks} chunks"
    )


@router.post(
    "/ingest",
    response_model=IngestionResponse,
    summary="Ingest URLs",
    description="Start ingestion of specified URLs into the knowledge base",
)
async def ingest_urls(
    request: IngestionRequest,
    background_tasks: BackgroundTasks,
) -> IngestionResponse:
    """
    Start ingestion of URLs.

    The ingestion runs in the background. Check stats endpoint for progress.
    """
    logger.info(f"Ingestion requested for {len(request.urls)} URLs")

    # Start ingestion in background
    background_tasks.add_task(run_ingestion, request.urls)

    return IngestionResponse(
        success=True,
        message=f"Ingestion started for {len(request.urls)} URLs",
        stats={"urls_queued": len(request.urls)},
    )


@router.post(
    "/ingest/taxes",
    response_model=IngestionResponse,
    summary="Ingest tax section",
    description="Start ingestion of the pre-configured Canada.ca tax section URLs",
)
async def ingest_taxes(
    background_tasks: BackgroundTasks,
) -> IngestionResponse:
    """
    Start ingestion of all tax-related URLs.

    Uses the pre-configured list of tax section URLs.
    """
    logger.info(f"Tax section ingestion requested ({len(CANADA_TAX_URLS)} URLs)")

    # Start ingestion in background
    background_tasks.add_task(run_ingestion, CANADA_TAX_URLS)

    return IngestionResponse(
        success=True,
        message=f"Tax section ingestion started ({len(CANADA_TAX_URLS)} URLs)",
        stats={"urls_queued": len(CANADA_TAX_URLS)},
    )


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Get system statistics",
    description="Get counts of documents, chunks, and sessions",
)
async def get_stats(
    db: AsyncSession = Depends(get_db_session),
) -> StatsResponse:
    """Get system statistics."""
    from sqlalchemy import func, select
    from src.db.models import Document
    
    doc_repo = DocumentRepository(db)

    documents = await doc_repo.get_document_count()
    chunks = await doc_repo.get_chunk_count()
    
    # Get the most recent scrape date
    result = await db.execute(
        select(func.max(Document.last_scraped_at))
    )
    last_updated = result.scalar()

    return StatsResponse(
        documents=documents,
        chunks=chunks,
        last_updated=last_updated.isoformat() if last_updated else None,
    )


@router.get(
    "/documents",
    summary="List documents",
    description="List all ingested documents",
)
async def list_documents(
    language: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    """List ingested documents."""
    doc_repo = DocumentRepository(db)

    documents = await doc_repo.list_all(
        language=language,
        limit=limit,
        offset=offset,
    )

    return [
        {
            "id": doc.id,
            "url": doc.url,
            "title": doc.title,
            "language": doc.language,
            "created_at": doc.created_at.isoformat(),
            "updated_at": doc.updated_at.isoformat(),
        }
        for doc in documents
    ]


@router.delete(
    "/documents/{doc_id}",
    summary="Delete a document",
    description="Delete a document and all its chunks",
)
async def delete_document(
    doc_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Delete a document."""
    doc_repo = DocumentRepository(db)

    deleted = await doc_repo.delete(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"status": "deleted", "document_id": doc_id}
