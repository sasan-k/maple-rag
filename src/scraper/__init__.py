"""Web scraper module."""

from src.scraper.crawler import CanadaCrawler, ScrapedPage
from src.scraper.chunker import ContentChunker
from src.scraper.ingestion import IngestionPipeline
from src.scraper.sitemap import SitemapParser, SitemapURL, discover_urls_from_sitemap

__all__ = [
    "CanadaCrawler",
    "ScrapedPage",
    "ContentChunker",
    "IngestionPipeline",
    "SitemapParser",
    "SitemapURL",
    "discover_urls_from_sitemap",
]

