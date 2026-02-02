#!/usr/bin/env python
"""
Manual script to run the scraper and ingest content.

Usage:
    python scripts/run_scraper.py
    python scripts/run_scraper.py --url https://www.canada.ca/en/services/taxes.html
    python scripts/run_scraper.py --all-taxes
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.logging import setup_logging, get_logger
from src.scraper.ingestion import (
    IngestionPipeline,
    CANADA_TAX_URLS,
    CANADA_TAX_URLS_FR,
)

logger = get_logger("scripts.scraper")


async def run_ingestion(urls: list[str]) -> None:
    """Run the ingestion pipeline."""
    logger.info(f"Starting ingestion of {len(urls)} URLs")

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


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Canada.ca content scraper and ingestion tool"
    )
    parser.add_argument(
        "--url",
        "-u",
        type=str,
        help="Single URL to ingest",
    )
    parser.add_argument(
        "--urls",
        type=str,
        nargs="+",
        help="Multiple URLs to ingest",
    )
    parser.add_argument(
        "--all-taxes",
        action="store_true",
        help="Ingest all pre-configured tax URLs (EN and FR)",
    )
    parser.add_argument(
        "--taxes-en",
        action="store_true",
        help="Ingest English tax URLs only",
    )
    parser.add_argument(
        "--crawl-only",
        action="store_true",
        help="Only crawl, don't store (for testing)",
    )
    parser.add_argument(
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
    else:
        # Default to a few sample URLs
        urls = [
            "https://www.canada.ca/en/services/taxes.html",
            "https://www.canada.ca/en/services/taxes/income-tax.html",
        ]

    # Run
    if args.crawl_only and args.url:
        asyncio.run(crawl_only(args.url))
    else:
        asyncio.run(run_ingestion(urls))


if __name__ == "__main__":
    main()
