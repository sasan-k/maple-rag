"""
Web crawler for canada.ca pages.

Handles scraping, HTML parsing, and content extraction.
"""

import asyncio
import re
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger("scraper")


@dataclass
class ScrapedPage:
    """Represents a scraped page from canada.ca."""

    url: str
    title: str
    content: str
    language: str
    html: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        """Get approximate word count."""
        return len(self.content.split())


class CanadaCrawler:
    """
    Web crawler for canada.ca pages.

    Handles respectful crawling with rate limiting and proper user agent.
    """

    # Selectors for main content on canada.ca
    CONTENT_SELECTORS = [
        "main",
        "article",
        ".mwsgeneric-base-html",
        "#wb-main",
        ".container.main-content",
    ]

    # Elements to remove from content
    REMOVE_SELECTORS = [
        "script",
        "style",
        "nav",
        "header",
        "footer",
        ".gcweb-menu",
        ".wb-gcslb",
        "#wb-bc",  # Breadcrumb
        ".pagedetails",
        ".noprint",
        ".wb-inv",  # Screen reader only content
        ".mfp-hide",
    ]

    def __init__(
        self,
        base_urls: list[str] | None = None,
        rate_limit: float | None = None,
        follow_links: bool = False,
        max_depth: int = 1,
    ):
        """
        Initialize the crawler.

        Args:
            base_urls: List of URLs to crawl
            rate_limit: Seconds to wait between requests
            follow_links: Whether to follow links on pages
            max_depth: Maximum link following depth
        """
        settings = get_settings()

        self.base_urls = base_urls or []
        self.rate_limit = rate_limit or settings.scraper_rate_limit_seconds
        self.follow_links = follow_links
        self.max_depth = max_depth
        self.user_agent = settings.scraper_user_agent
        self.timeout = settings.scraper_timeout_seconds

        # Track visited URLs to avoid duplicates
        self._visited: set[str] = set()

    def add_url(self, url: str) -> None:
        """Add a URL to the crawl list."""
        if url not in self.base_urls:
            self.base_urls.append(url)

    def add_urls(self, urls: list[str]) -> None:
        """Add multiple URLs to the crawl list."""
        for url in urls:
            self.add_url(url)

    async def crawl(self) -> AsyncGenerator[ScrapedPage, None]:
        """
        Crawl all configured URLs.

        Yields:
            ScrapedPage objects for each successfully scraped page
        """
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": self.user_agent},
        ) as client:
            for url in self.base_urls:
                if url in self._visited:
                    continue

                try:
                    async for page in self._crawl_url(client, url, depth=0):
                        yield page
                except Exception as e:
                    logger.error(f"Error crawling {url}: {e}")
                    continue

    async def crawl_single(self, url: str) -> ScrapedPage | None:
        """
        Crawl a single URL.

        Args:
            url: The URL to crawl

        Returns:
            ScrapedPage or None if failed
        """
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": self.user_agent},
        ) as client:
            try:
                return await self._fetch_and_parse(client, url)
            except Exception as e:
                logger.error(f"Error crawling {url}: {e}")
                return None

    async def _crawl_url(
        self,
        client: httpx.AsyncClient,
        url: str,
        depth: int = 0,
    ) -> AsyncGenerator[ScrapedPage, None]:
        """Crawl a URL and optionally follow links."""
        if url in self._visited:
            return

        self._visited.add(url)
        logger.info(f"Crawling: {url}")

        try:
            page = await self._fetch_and_parse(client, url)
            yield page

            # Rate limiting
            await asyncio.sleep(self.rate_limit)

            # Follow links if enabled and within depth
            if self.follow_links and depth < self.max_depth:
                links = self._extract_links(page.html, url)
                for link in links:
                    if link not in self._visited:
                        async for linked_page in self._crawl_url(
                            client, link, depth + 1
                        ):
                            yield linked_page

        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP error for {url}: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.warning(f"Request error for {url}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {e}")

    async def _fetch_and_parse(
        self,
        client: httpx.AsyncClient,
        url: str,
    ) -> ScrapedPage:
        """Fetch a URL and parse its content."""
        response = await client.get(url)
        response.raise_for_status()

        html = response.text
        soup = BeautifulSoup(html, "lxml")

        # Extract title
        title = self._extract_title(soup)

        # Extract main content
        content = self._extract_content(soup)

        # Detect language
        language = self._detect_language(url, soup)

        return ScrapedPage(
            url=str(response.url),  # Use final URL after redirects
            title=title,
            content=content,
            language=language,
            html=html,
            metadata={
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "status_code": response.status_code,
                "content_length": len(content),
                "word_count": len(content.split()),
            },
        )

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract the page title."""
        # Try h1 first
        h1 = soup.select_one("h1")
        if h1:
            return self._clean_text(h1.get_text())

        # Fall back to title tag
        title_tag = soup.select_one("title")
        if title_tag:
            title = self._clean_text(title_tag.get_text())
            # Remove " - Canada.ca" suffix
            title = re.sub(r"\s*[-–—]\s*Canada\.ca\s*$", "", title)
            return title

        return "Untitled"

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract the main content from the page."""
        # Remove unwanted elements
        for selector in self.REMOVE_SELECTORS:
            for element in soup.select(selector):
                element.decompose()

        # Find main content area
        main_content = None
        for selector in self.CONTENT_SELECTORS:
            main_content = soup.select_one(selector)
            if main_content:
                break

        if not main_content:
            main_content = soup.body or soup

        # Extract text
        text = self._extract_text_with_structure(main_content)
        return self._clean_text(text)

    def _extract_text_with_structure(self, element: Tag | NavigableString) -> str:
        """
        Extract text while preserving some structure.

        Adds newlines for block elements to maintain readability.
        """
        if isinstance(element, NavigableString):
            return str(element)

        block_elements = {
            "p",
            "div",
            "section",
            "article",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "li",
            "tr",
            "br",
        }

        text_parts = []

        for child in element.children:
            if isinstance(child, NavigableString):
                text_parts.append(str(child))
            elif isinstance(child, Tag):
                child_text = self._extract_text_with_structure(child)
                if child.name in block_elements:
                    text_parts.append(f"\n{child_text}\n")
                else:
                    text_parts.append(child_text)

        return "".join(text_parts)

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Replace multiple whitespace with single space
        text = re.sub(r"[ \t]+", " ", text)
        # Replace multiple newlines with double newline
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        # Strip leading/trailing whitespace
        text = text.strip()
        return text

    def _detect_language(self, url: str, soup: BeautifulSoup) -> str:
        """
        Detect the page language.

        canada.ca uses /en/ and /fr/ in URLs.
        """
        # Check URL pattern
        if "/fr/" in url or url.endswith("/fr"):
            return "fr"
        if "/en/" in url or url.endswith("/en"):
            return "en"

        # Check html lang attribute
        html_tag = soup.find("html")
        if html_tag and isinstance(html_tag, Tag):
            lang = html_tag.get("lang", "")
            if isinstance(lang, str):
                if lang.startswith("fr"):
                    return "fr"
                if lang.startswith("en"):
                    return "en"

        # Default to English
        return "en"

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        """Extract internal canada.ca links from a page."""
        soup = BeautifulSoup(html, "lxml")
        links = []

        parsed_base = urlparse(base_url)
        base_domain = parsed_base.netloc

        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if isinstance(href, list):
                href = href[0]

            # Skip anchors, javascript, mailto
            if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            # Build absolute URL
            full_url = urljoin(base_url, href)
            parsed = urlparse(full_url)

            # Only include canada.ca links
            if parsed.netloc == base_domain or parsed.netloc.endswith(".canada.ca"):
                # Remove fragment
                clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if parsed.query:
                    clean_url += f"?{parsed.query}"
                links.append(clean_url)

        return list(set(links))
