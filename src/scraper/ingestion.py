"""
Ingestion pipeline for processing and storing scraped content.

Orchestrates crawling, chunking, embedding, and storage.
"""

from dataclasses import dataclass

from src.config.logging import get_logger
from src.db.connection import get_db
from src.db.repositories.document import DocumentRepository
from src.llm.factory import EmbeddingFactory
from src.scraper.chunker import ContentChunker
from src.scraper.crawler import CanadaCrawler, ScrapedPage

logger = get_logger("ingestion")


@dataclass
class IngestionResult:
    """Result of an ingestion operation."""

    url: str
    success: bool
    document_id: str | None = None
    chunks_created: int = 0
    was_updated: bool = False
    error: str | None = None


@dataclass
class IngestionStats:
    """Statistics for a full ingestion run."""

    total_urls: int = 0
    successful: int = 0
    failed: int = 0
    new_documents: int = 0
    updated_documents: int = 0
    unchanged_documents: int = 0
    total_chunks: int = 0
    results: list[IngestionResult] | None = None


class IngestionPipeline:
    """
    Pipeline for ingesting content from canada.ca.

    Handles the full flow from crawling to storage.
    """

    def __init__(
        self,
        urls: list[str] | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        """
        Initialize the ingestion pipeline.

        Args:
            urls: List of URLs to ingest
            chunk_size: Override default chunk size
            chunk_overlap: Override default chunk overlap
        """
        self.crawler = CanadaCrawler(base_urls=urls or [])
        self.chunker = ContentChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        self._embeddings = None

    @property
    def embeddings(self):
        """Lazy load embeddings model."""
        if self._embeddings is None:
            self._embeddings = EmbeddingFactory.create_embeddings()
        return self._embeddings

    def add_url(self, url: str) -> None:
        """Add a URL to ingest."""
        self.crawler.add_url(url)

    def add_urls(self, urls: list[str]) -> None:
        """Add multiple URLs to ingest."""
        self.crawler.add_urls(urls)

    async def ingest_page(self, page: ScrapedPage) -> IngestionResult:
        """
        Ingest a single scraped page.

        Args:
            page: ScrapedPage object

        Returns:
            IngestionResult with status
        """
        logger.info(f"Ingesting page: {page.url}")

        try:
            async with get_db() as db:
                doc_repo = DocumentRepository(db)

                # Upsert document
                document, was_created = await doc_repo.upsert(
                    url=page.url,
                    title=page.title,
                    content=page.content,
                    language=page.language,
                    metadata=page.metadata,
                )

                # If document unchanged, skip re-chunking
                if not was_created and document.content_hash:
                    new_hash = doc_repo.compute_hash(page.content)
                    if document.content_hash == new_hash:
                        logger.info(f"Document unchanged: {page.url}")
                        return IngestionResult(
                            url=page.url,
                            success=True,
                            document_id=document.id,
                            chunks_created=0,
                            was_updated=False,
                        )

                # Delete old chunks
                await doc_repo.delete_chunks(document.id)

                # Create new chunks
                chunks = self.chunker.chunk_document(
                    content=page.content,
                    url=page.url,
                    title=page.title,
                    language=page.language,
                    extra_metadata=page.metadata,
                )

                if not chunks:
                    logger.warning(f"No chunks created for: {page.url}")
                    return IngestionResult(
                        url=page.url,
                        success=True,
                        document_id=document.id,
                        chunks_created=0,
                        was_updated=was_created,
                    )

                # Generate embeddings
                logger.info(f"Generating embeddings for {len(chunks)} chunks")
                chunk_texts = [c.content for c in chunks]
                embeddings = await self.embeddings.aembed_documents(chunk_texts)

                # Store chunks with embeddings
                chunk_data = [
                    {
                        "content": chunk.content,
                        "embedding": embedding,
                        "chunk_index": chunk.chunk_index,
                        "metadata": chunk.metadata,
                    }
                    for chunk, embedding in zip(chunks, embeddings)
                ]

                await doc_repo.add_chunks_batch(document.id, chunk_data)

                logger.info(f"Ingested {len(chunks)} chunks for: {page.url}")

                return IngestionResult(
                    url=page.url,
                    success=True,
                    document_id=document.id,
                    chunks_created=len(chunks),
                    was_updated=not was_created,
                )

        except Exception as e:
            logger.error(f"Error ingesting {page.url}: {e}")
            return IngestionResult(
                url=page.url,
                success=False,
                error=str(e),
            )

    async def ingest_url(self, url: str) -> IngestionResult:
        """
        Ingest a single URL.

        Args:
            url: URL to ingest

        Returns:
            IngestionResult with status
        """
        page = await self.crawler.crawl_single(url)
        if page is None:
            return IngestionResult(
                url=url,
                success=False,
                error="Failed to crawl page",
            )

        return await self.ingest_page(page)

    async def run(self) -> IngestionStats:
        """
        Run the full ingestion pipeline.

        Crawls all configured URLs and ingests their content.

        Returns:
            IngestionStats with summary
        """
        stats = IngestionStats(
            total_urls=len(self.crawler.base_urls),
            results=[],
        )

        async for page in self.crawler.crawl():
            result = await self.ingest_page(page)
            stats.results.append(result)

            if result.success:
                stats.successful += 1
                stats.total_chunks += result.chunks_created

                if result.chunks_created > 0:
                    if result.was_updated:
                        stats.updated_documents += 1
                    else:
                        stats.new_documents += 1
                else:
                    stats.unchanged_documents += 1
            else:
                stats.failed += 1

        logger.info(
            f"Ingestion complete: {stats.successful} successful, "
            f"{stats.failed} failed, {stats.total_chunks} chunks"
        )

        return stats


# Pre-configured URL sets for different canada.ca sections
CANADA_TAX_URLS = [
    "https://www.canada.ca/en/services/taxes.html",
    "https://www.canada.ca/en/services/taxes/income-tax.html",
    "https://www.canada.ca/en/services/taxes/income-tax/personal-income-tax.html",
    "https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/about-your-tax-return.html",
    "https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/about-your-tax-return/tax-return/completing-a-tax-return/deductions-credits-expenses.html",
    "https://www.canada.ca/en/revenue-agency/services/child-family-benefits.html",
    "https://www.canada.ca/en/services/taxes/child-and-family-benefits.html",
    "https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/gst-hst-businesses.html",
]

CANADA_TAX_URLS_FR = [
    "https://www.canada.ca/fr/services/impots.html",
    "https://www.canada.ca/fr/services/impots/impot-sur-le-revenu.html",
]
