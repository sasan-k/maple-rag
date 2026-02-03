#!/usr/bin/env python
"""
Incremental ingestion script.

Fetches sitemap, detects changes, and only scrapes/updates modified pages.

Usage:
    # Scrape all tax pages
    uv run python scripts/incremental_ingest.py --filter "/en/services/taxes/"

    # Scrape business tax pages only
    uv run python scripts/incremental_ingest.py --filter "/en/services/taxes/income-tax/business"

    # Force full re-index
    uv run python scripts/incremental_ingest.py --full-reindex

    # Dry run (show what would be done)
    uv run python scripts/incremental_ingest.py --filter "/en/services/taxes/" --dry-run
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()


async def run_incremental_ingest(
    filter_pattern: str | None = None,
    sitemap_url: str = "https://www.canada.ca/en/revenue-agency.sitemap.xml",
    max_pages: int | None = None,
    dry_run: bool = False,
    full_reindex: bool = False,
):
    """
    Run incremental ingestion.

    Args:
        filter_pattern: URL pattern to filter (e.g., "/en/services/taxes/")
        sitemap_url: URL of the sitemap to fetch
        max_pages: Maximum number of pages to process
        dry_run: If True, only show what would be done
        full_reindex: If True, reprocess all pages regardless of changes
    """
    from src.config.settings import get_settings
    from src.db.connection import get_db
    from src.db.repositories.document import DocumentRepository
    from src.llm.factory import EmbeddingFactory
    from src.scraper.change_detector import ChangeDetector, ChangeReport
    from src.scraper.chunker import ContentChunker
    from src.scraper.crawler import CanadaCrawler
    from src.scraper.sitemap import SitemapParser, URLFilter

    settings = get_settings()

    print("=" * 70)
    print("INCREMENTAL INGESTION")
    print("=" * 70)
    print(f"Sitemap URL: {sitemap_url}")
    print(f"Filter: {filter_pattern or 'None'}")
    print(f"Dry Run: {dry_run}")
    print(f"Full Reindex: {full_reindex}")
    print("=" * 70)

    # Step 1: Fetch sitemap
    print("\n[STEP 1] Fetching sitemap...")

    async with SitemapParser() as parser:
        all_urls = await parser.get_sitemap_urls(sitemap_url)

    print(f"  Found {len(all_urls)} URLs in sitemap")

    # Apply filter
    if filter_pattern:
        all_urls = [u for u in all_urls if filter_pattern in u.loc]
        print(f"  After filtering: {len(all_urls)} URLs match '{filter_pattern}'")

    # Apply URL filter (exclude PDFs, forms, etc.)
    url_filter = URLFilter()
    all_urls = url_filter.filter(all_urls)
    print(f"  After exclusions: {len(all_urls)} URLs")

    if not all_urls:
        print("\n[INFO] No URLs to process.")
        return

    # Step 2: Detect changes
    print("\n[STEP 2] Detecting changes...")

    async with get_db() as db:
        detector = ChangeDetector(db)

        if full_reindex:
            # Treat all URLs as changed
            report = ChangeReport(
                new_urls=[],
                changed_urls=all_urls,
                unchanged_urls=[],
                deleted_urls=[],
            )
            print("  Full reindex - treating all URLs as changed")
        else:
            report = await detector.detect_changes(all_urls)

    print(f"\n{report.summary()}")

    if report.total_to_process == 0:
        print("\n[INFO] No changes detected. Database is up to date.")
        return

    if dry_run:
        print("\n[DRY RUN] Would process:")
        for url in (report.new_urls + report.changed_urls)[:10]:
            print(f"  - {url.loc}")
        if report.total_to_process > 10:
            print(f"  ... and {report.total_to_process - 10} more")
        return

    # Step 3: Scrape and update
    print("\n[STEP 3] Scraping and updating...")

    urls_to_process = report.new_urls + report.changed_urls
    if max_pages:
        urls_to_process = urls_to_process[:max_pages]
        print(f"  Limited to {max_pages} pages")

    # Initialize components
    embeddings = EmbeddingFactory.create_embeddings()
    chunker = ContentChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    processed = 0
    failed = 0

    for entry in urls_to_process:
        url = entry.loc
        print(f"\n  Processing: {url}")

        try:
            # Scrape the page
            crawler = CanadaCrawler(base_urls=[url], max_depth=0)
            page = None
            async for p in crawler.crawl():
                page = p
                break

            if not page:
                print("    [FAILED] Could not fetch page")
                failed += 1
                continue

            async with get_db() as db:
                doc_repo = DocumentRepository(db)

                # Check if content actually changed (by hash)
                existing_doc = await doc_repo.get_by_url(url)
                new_hash = doc_repo.compute_hash(page.content)

                if (
                    existing_doc
                    and existing_doc.content_hash == new_hash
                    and not full_reindex
                ):
                    print("    [SKIP] Content unchanged (hash match)")
                    # Update sitemap_lastmod but skip re-embedding
                    existing_doc.sitemap_lastmod = entry.lastmod
                    existing_doc.last_scraped_at = datetime.now(timezone.utc)
                    existing_doc.scrape_status = "scraped"
                    await db.commit()
                    continue

                # Upsert document
                doc, created = await doc_repo.upsert(
                    url=page.url,
                    title=page.title,
                    content=page.content,
                    language=page.language,
                )

                # Update additional fields
                doc.sitemap_lastmod = entry.lastmod
                doc.last_scraped_at = datetime.now(timezone.utc)
                doc.scrape_status = "scraped"
                doc.embedding_version = settings.aws_bedrock_embedding_model_id

                # Create chunks
                chunks = chunker.chunk_document(
                    content=page.content,
                    url=page.url,
                    title=page.title,
                    language=page.language,
                )

                # Generate embeddings
                texts = [c.content for c in chunks]
                vectors = embeddings.embed_documents(texts)

                # Delete old chunks and add new
                await doc_repo.delete_chunks(doc.id)
                for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
                    await doc_repo.add_chunk(
                        document_id=doc.id,
                        content=chunk.content,
                        embedding=vec,
                        chunk_index=i,
                        metadata=chunk.metadata,
                    )

                await db.commit()

                action = "Created" if created else "Updated"
                print(f"    [OK] {action} with {len(chunks)} chunks")
                processed += 1

        except Exception as e:
            print(f"    [FAILED] {e}")
            failed += 1

            # Mark as failed in database
            try:
                async with get_db() as db:
                    from sqlalchemy import update

                    from src.db.models import Document

                    await db.execute(
                        update(Document)
                        .where(Document.url == url)
                        .values(scrape_status="failed")
                    )
                    await db.commit()
            except Exception:
                pass

    # Step 4: Handle deletions (optional)
    if report.deleted_urls:
        print(f"\n[STEP 4] Handling {len(report.deleted_urls)} deleted URLs...")
        async with get_db() as db:
            detector = ChangeDetector(db)
            await detector.mark_deleted(report.deleted_urls, soft_delete=True)

    # Summary
    print("\n" + "=" * 70)
    print("INGESTION COMPLETE")
    print("=" * 70)
    print(f"  Processed: {processed}")
    print(f"  Failed: {failed}")
    print(f"  Skipped (unchanged): {len(report.unchanged_urls)}")
    print(f"  Deleted: {len(report.deleted_urls)}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Incremental ingestion from canada.ca sitemap"
    )
    parser.add_argument(
        "--filter",
        type=str,
        default=None,
        help="URL pattern to filter (e.g., '/en/revenue-agency/services/tax/')",
    )
    parser.add_argument(
        "--sitemap",
        type=str,
        default="https://www.canada.ca/en/revenue-agency.sitemap.xml",
        help="Sitemap URL to fetch",
    )
    parser.add_argument(
        "--max-pages", type=int, default=None, help="Maximum pages to process"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--full-reindex", action="store_true", help="Force reprocessing of all pages"
    )

    args = parser.parse_args()

    asyncio.run(
        run_incremental_ingest(
            filter_pattern=args.filter,
            sitemap_url=args.sitemap,
            max_pages=args.max_pages,
            dry_run=args.dry_run,
            full_reindex=args.full_reindex,
        )
    )


if __name__ == "__main__":
    main()
