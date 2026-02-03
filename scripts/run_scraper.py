#!/usr/bin/env python
"""
Manual script to run the scraper and ingest content.

Usage:
    python scripts/run_scraper.py
    python scripts/run_scraper.py --url https://www.canada.ca/en/services/taxes.html
    python scripts/run_scraper.py --all-taxes
    python scripts/run_scraper.py --sitemap https://www.canada.ca/en/revenue-agency.sitemap.xml
    python scripts/run_scraper.py --discover-taxes
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.logging import get_logger, setup_logging
from src.scraper.ingestion import (
    CANADA_TAX_URLS,
    CANADA_TAX_URLS_FR,
    IngestionPipeline,
)

logger = get_logger("scripts.scraper")


async def run_ingestion(urls: list[str], dry_run: bool = False) -> None:
    """Run the ingestion pipeline."""
    logger.info(f"Starting ingestion of {len(urls)} URLs")

    if dry_run:
        print("\n" + "=" * 60)
        print("DRY RUN - URLs that would be processed:")
        print("=" * 60)
        for url in urls:
            print(f"  • {url}")
        print(f"\nTotal: {len(urls)} URLs")
        print("=" * 60)
        return

    pipeline = IngestionPipeline(urls=urls)
    stats = await pipeline.run()

    # Print results
    print("\n" + "=" * 60)
    print("INGESTION COMPLETE")
    print("=" * 60)
    print(f"Total URLs:        {stats.total_urls}")
    print(f"Successful:        {stats.successful}")
    print(f"Failed:            {stats.failed}")
    print(f"New documents:     {stats.new_documents}")
    print(f"Updated:           {stats.updated_documents}")
    print(f"Unchanged:         {stats.unchanged_documents}")
    print(f"Total chunks:      {stats.total_chunks}")
    print("=" * 60)

    if stats.results:
        print("\nDetails:")
        for result in stats.results:
            status = "✓" if result.success else "✗"
            print(f"  {status} {result.url}")
            if result.error:
                print(f"    Error: {result.error}")
            elif result.chunks_created:
                print(f"    Chunks: {result.chunks_created}")


async def crawl_only(url: str) -> None:
    """Crawl a single URL without storing (for testing)."""
    from src.scraper.crawler import CanadaCrawler

    logger.info(f"Crawling: {url}")

    crawler = CanadaCrawler()
    page = await crawler.crawl_single(url)

    if page:
        print("\n" + "=" * 60)
        print("CRAWL RESULT")
        print("=" * 60)
        print(f"URL:       {page.url}")
        print(f"Title:     {page.title}")
        print(f"Language:  {page.language}")
        print(f"Words:     {page.word_count}")
        print("-" * 60)
        print("Content preview (first 500 chars):")
        print(page.content[:500])
        print("..." if len(page.content) > 500 else "")
        print("=" * 60)
    else:
        print(f"Failed to crawl: {url}")


async def discover_from_sitemap(
    sitemap_url: str,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    modified_days: int | None = None,
) -> list[str]:
    """Discover URLs from a sitemap."""
    from src.scraper.sitemap import discover_urls_from_sitemap

    modified_since = None
    if modified_days:
        modified_since = datetime.now() - timedelta(days=modified_days)

    print(f"\nDiscovering URLs from: {sitemap_url}")
    if modified_since:
        print(f"Modified since: {modified_since.date()}")

    urls = await discover_urls_from_sitemap(
        sitemap_url,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
        modified_since=modified_since,
    )

    print(f"Found {len(urls)} URLs")
    return urls


async def discover_tax_urls(
    include_french: bool = True,
    modified_days: int | None = None,
) -> list[str]:
    """Discover tax-related URLs from CRA sitemaps."""
    from src.scraper.sitemap import SitemapParser

    modified_since = None
    if modified_days:
        modified_since = datetime.now() - timedelta(days=modified_days)

    print("\nDiscovering tax-related URLs from canada.ca sitemaps...")
    if modified_since:
        print(f"Modified since: {modified_since.date()}")

    async with SitemapParser() as parser:
        urls = await parser.discover_tax_urls(
            include_french=include_french,
            modified_since=modified_since,
        )

    url_strings = [u.loc for u in urls]
    print(f"Found {len(url_strings)} tax-related URLs")
    return url_strings


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Canada.ca content scraper and ingestion tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test crawl a single URL (no database)
  python scripts/run_scraper.py --crawl-only --url https://www.canada.ca/en/services/taxes.html

  # Ingest a single URL
  python scripts/run_scraper.py --url https://www.canada.ca/en/services/taxes.html

  # Ingest pre-configured tax URLs (English only)
  python scripts/run_scraper.py --taxes-en

  # Ingest all tax URLs (English + French)
  python scripts/run_scraper.py --all-taxes

  # Discover URLs from CRA sitemap and ingest
  python scripts/run_scraper.py --discover-taxes

  # Discover from custom sitemap
  python scripts/run_scraper.py --sitemap https://www.canada.ca/en/revenue-agency.sitemap.xml

  # Only show what would be ingested (dry run)
  python scripts/run_scraper.py --discover-taxes --dry-run

  # Ingest only pages modified in last 7 days
  python scripts/run_scraper.py --discover-taxes --modified-days 7
        """,
    )

    # URL Source Options (mutually exclusive)
    source_group = parser.add_argument_group("URL Sources")
    source_group.add_argument(
        "--url",
        "-u",
        type=str,
        help="Single URL to ingest",
    )
    source_group.add_argument(
        "--urls",
        type=str,
        nargs="+",
        help="Multiple URLs to ingest",
    )
    source_group.add_argument(
        "--all-taxes",
        action="store_true",
        help="Ingest all pre-configured tax URLs (EN and FR)",
    )
    source_group.add_argument(
        "--taxes-en",
        action="store_true",
        help="Ingest English tax URLs only",
    )
    source_group.add_argument(
        "--sitemap",
        type=str,
        help="Discover URLs from a sitemap XML",
    )
    source_group.add_argument(
        "--discover-taxes",
        action="store_true",
        help="Discover tax URLs from CRA sitemaps",
    )

    # Filter Options
    filter_group = parser.add_argument_group("Filters")
    filter_group.add_argument(
        "--include",
        type=str,
        nargs="+",
        help="URL patterns to include (regex)",
    )
    filter_group.add_argument(
        "--exclude",
        type=str,
        nargs="+",
        help="URL patterns to exclude (regex)",
    )
    filter_group.add_argument(
        "--modified-days",
        type=int,
        help="Only include pages modified within N days",
    )
    filter_group.add_argument(
        "--no-french",
        action="store_true",
        help="Exclude French pages",
    )

    # Operation Options
    op_group = parser.add_argument_group("Operations")
    op_group.add_argument(
        "--crawl-only",
        action="store_true",
        help="Only crawl, don't store (for testing)",
    )
    op_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be ingested, don't actually do it",
    )
    op_group.add_argument(
        "--limit",
        type=int,
        help="Limit number of URLs to process",
    )
    op_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    # Set up logging
    setup_logging()

    # Determine URLs to process
    urls: list[str] = []

    if args.url:
        urls = [args.url]
    elif args.urls:
        urls = args.urls
    elif args.all_taxes:
        urls = CANADA_TAX_URLS + CANADA_TAX_URLS_FR
    elif args.taxes_en:
        urls = CANADA_TAX_URLS
    elif args.sitemap:
        urls = asyncio.run(
            discover_from_sitemap(
                args.sitemap,
                include_patterns=args.include,
                exclude_patterns=args.exclude,
                modified_days=args.modified_days,
            )
        )
    elif args.discover_taxes:
        urls = asyncio.run(
            discover_tax_urls(
                include_french=not args.no_french,
                modified_days=args.modified_days,
            )
        )
    else:
        # Default to a few sample URLs
        urls = [
            "https://www.canada.ca/en/services/taxes.html",
            "https://www.canada.ca/en/services/taxes/income-tax.html",
        ]

    # Apply limit
    if args.limit and len(urls) > args.limit:
        print(f"\nLimiting to first {args.limit} URLs (of {len(urls)} total)")
        urls = urls[: args.limit]

    # Run
    if args.crawl_only and args.url:
        asyncio.run(crawl_only(args.url))
    else:
        asyncio.run(run_ingestion(urls, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
