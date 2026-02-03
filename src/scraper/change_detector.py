"""
Change detection for incremental scraping.

Compares sitemap entries with database to detect new, changed, and deleted pages.
"""

from dataclasses import dataclass, field

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logging import get_logger
from src.db.connection import get_db
from src.db.models import Document
from src.scraper.sitemap import SitemapURL

logger = get_logger("scraper.change_detector")


@dataclass
class ChangeReport:
    """Report of detected changes between sitemap and database."""

    new_urls: list[SitemapURL] = field(default_factory=list)
    changed_urls: list[SitemapURL] = field(default_factory=list)
    unchanged_urls: list[SitemapURL] = field(default_factory=list)
    deleted_urls: list[str] = field(default_factory=list)

    @property
    def total_to_process(self) -> int:
        """Total URLs that need processing (new + changed)."""
        return len(self.new_urls) + len(self.changed_urls)

    def summary(self) -> str:
        """Return a human-readable summary."""
        return (
            f"Change Report:\n"
            f"  New:       {len(self.new_urls)}\n"
            f"  Changed:   {len(self.changed_urls)}\n"
            f"  Unchanged: {len(self.unchanged_urls)}\n"
            f"  Deleted:   {len(self.deleted_urls)}\n"
            f"  To Process: {self.total_to_process}"
        )


class ChangeDetector:
    """
    Detects changes between sitemap and database.
    
    Compares:
    - URLs in sitemap vs URLs in database
    - lastmod dates to detect content changes
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize the change detector.
        
        Args:
            session: Database session
        """
        self.session = session

    async def get_existing_documents(self) -> dict[str, Document]:
        """
        Get all existing documents from the database.
        
        Returns:
            Dict mapping URL to Document
        """
        result = await self.session.execute(
            select(Document).where(Document.scrape_status != "deleted")
        )
        documents = result.scalars().all()
        return {doc.url: doc for doc in documents}

    async def detect_changes(
        self,
        sitemap_entries: list[SitemapURL],
        check_deleted: bool = True,
    ) -> ChangeReport:
        """
        Detect changes between sitemap entries and database.
        
        Args:
            sitemap_entries: List of SitemapURL from sitemap
            check_deleted: Whether to check for deleted URLs
            
        Returns:
            ChangeReport with categorized URLs
        """
        report = ChangeReport()

        # Get existing documents
        existing_docs = await self.get_existing_documents()
        existing_urls = set(existing_docs.keys())
        sitemap_urls = {entry.url for entry in sitemap_entries}

        logger.info(f"Comparing {len(sitemap_entries)} sitemap URLs with {len(existing_docs)} database documents")

        for entry in sitemap_entries:
            url = entry.url

            if url not in existing_docs:
                # New URL - not in database
                report.new_urls.append(entry)
                logger.debug(f"NEW: {url}")
            else:
                doc = existing_docs[url]

                # Check if content has changed based on lastmod
                if entry.lastmod and doc.sitemap_lastmod:
                    if entry.lastmod > doc.sitemap_lastmod:
                        report.changed_urls.append(entry)
                        logger.debug(f"CHANGED: {url} (sitemap: {entry.lastmod}, db: {doc.sitemap_lastmod})")
                    else:
                        report.unchanged_urls.append(entry)
                elif entry.lastmod and not doc.sitemap_lastmod:
                    # First time seeing lastmod for this doc - check if we should update
                    report.changed_urls.append(entry)
                    logger.debug(f"CHANGED (no stored lastmod): {url}")
                else:
                    # No lastmod info - assume unchanged
                    report.unchanged_urls.append(entry)

        # Check for deleted URLs (in DB but not in sitemap)
        if check_deleted:
            deleted = existing_urls - sitemap_urls
            report.deleted_urls = list(deleted)
            if deleted:
                logger.info(f"Found {len(deleted)} URLs in database but not in sitemap")

        logger.info(report.summary())
        return report

    async def mark_urls_for_processing(
        self,
        urls: list[SitemapURL],
        status: str = "pending",
    ) -> int:
        """
        Mark URLs for processing in the database.
        
        Args:
            urls: List of SitemapURL to mark
            status: Status to set ('pending', 'changed')
            
        Returns:
            Number of URLs marked
        """
        count = 0
        for entry in urls:
            result = await self.session.execute(
                update(Document)
                .where(Document.url == entry.url)
                .values(
                    scrape_status=status,
                    sitemap_lastmod=entry.lastmod,
                )
            )
            if result.rowcount > 0:
                count += result.rowcount

        await self.session.commit()
        logger.info(f"Marked {count} URLs as '{status}'")
        return count

    async def mark_deleted(self, urls: list[str], soft_delete: bool = True) -> int:
        """
        Mark URLs as deleted.
        
        Args:
            urls: List of URLs to mark as deleted
            soft_delete: If True, mark as 'deleted'. If False, actually delete.
            
        Returns:
            Number of URLs processed
        """
        if not urls:
            return 0

        if soft_delete:
            count = 0
            for url in urls:
                result = await self.session.execute(
                    update(Document)
                    .where(Document.url == url)
                    .values(scrape_status="deleted")
                )
                count += result.rowcount
            await self.session.commit()
            logger.info(f"Soft-deleted {count} URLs")
            return count
        else:
            # Hard delete - remove from database
            from sqlalchemy import delete as sql_delete

            count = 0
            for url in urls:
                result = await self.session.execute(
                    sql_delete(Document).where(Document.url == url)
                )
                count += result.rowcount
            await self.session.commit()
            logger.info(f"Hard-deleted {count} URLs")
            return count


async def detect_changes_for_sitemap(
    sitemap_entries: list[SitemapURL],
) -> ChangeReport:
    """
    Convenience function to detect changes for a list of sitemap entries.
    
    Args:
        sitemap_entries: List of SitemapURL from sitemap
        
    Returns:
        ChangeReport with categorized URLs
    """
    async with get_db() as db:
        detector = ChangeDetector(db)
        return await detector.detect_changes(sitemap_entries)
