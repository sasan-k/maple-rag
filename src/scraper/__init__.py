"""Web scraper module."""

from src.scraper.crawler import CanadaCrawler, ScrapedPage
from src.scraper.chunker import ContentChunker
from src.scraper.ingestion import IngestionPipeline

__all__ = ["CanadaCrawler", "ScrapedPage", "ContentChunker", "IngestionPipeline"]
