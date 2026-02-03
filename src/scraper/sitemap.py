"""
Sitemap-based URL discovery for canada.ca.

Parses XML sitemaps to discover and filter URLs.
"""

import asyncio
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator

import httpx

from src.config.logging import get_logger

logger = get_logger("scraper.sitemap")

# Sitemap XML namespace
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


@dataclass
class SitemapURL:
    """Represents a URL from a sitemap."""

    loc: str
    lastmod: datetime | None = None
    changefreq: str | None = None
    priority: float | None = None

    @property
    def language(self) -> str:
        """Detect language from URL path."""
        if "/fr/" in self.loc or ".fr." in self.loc:
            return "fr"
        return "en"


@dataclass
class SitemapIndex:
    """Represents a sitemap index containing multiple sitemaps."""

    sitemaps: list[str] = field(default_factory=list)


class SitemapParser:
    """
    Parse XML sitemaps from canada.ca.

    Supports both sitemap index files and regular sitemaps.
    """

    def __init__(
        self,
        rate_limit: float = 1.0,
        timeout: float = 30.0,
    ):
        """
        Initialize the sitemap parser.

        Args:
            rate_limit: Seconds between requests
            timeout: Request timeout in seconds
        """
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        """Create HTTP client on context enter."""
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                "User-Agent": "CanadaCaBot/1.0 (RAG Research)",
                "Accept": "application/xml, text/xml",
            },
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *args):
        """Close HTTP client on context exit."""
        if self.client:
            await self.client.aclose()

    async def _fetch_xml(self, url: str) -> str | None:
        """Fetch XML content from URL."""
        try:
            if self.client is None:
                raise RuntimeError("Client not initialized")

            response = await self.client.get(url)
            response.raise_for_status()
            return response.text

        except Exception as e:
            logger.error(f"Failed to fetch sitemap {url}: {e}")
            return None

    def _parse_datetime(self, date_str: str) -> datetime | None:
        """Parse ISO datetime from sitemap."""
        if not date_str:
            return None

        try:
            # Handle various datetime formats
            # Format: 2026-01-27T11:05:03.823-05:00
            # Simplified parsing
            date_str = re.sub(r"\.\d+", "", date_str)  # Remove milliseconds
            date_str = re.sub(r"([+-]\d{2}):(\d{2})$", r"\1\2", date_str)  # Fix timezone

            for fmt in [
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d",
            ]:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

            return None

        except Exception:
            return None

    def _parse_sitemap_index(self, xml_content: str) -> SitemapIndex:
        """Parse a sitemap index XML."""
        index = SitemapIndex()

        try:
            root = ET.fromstring(xml_content)

            # Check if this is a sitemap index
            for sitemap in root.findall("sm:sitemap", SITEMAP_NS):
                loc = sitemap.find("sm:loc", SITEMAP_NS)
                if loc is not None and loc.text:
                    index.sitemaps.append(loc.text.strip())

        except ET.ParseError as e:
            logger.error(f"Failed to parse sitemap index: {e}")

        return index

    def _parse_url_sitemap(self, xml_content: str) -> list[SitemapURL]:
        """Parse a regular URL sitemap."""
        urls = []

        try:
            root = ET.fromstring(xml_content)

            for url_elem in root.findall("sm:url", SITEMAP_NS):
                loc = url_elem.find("sm:loc", SITEMAP_NS)
                if loc is None or not loc.text:
                    continue

                lastmod_elem = url_elem.find("sm:lastmod", SITEMAP_NS)
                changefreq_elem = url_elem.find("sm:changefreq", SITEMAP_NS)
                priority_elem = url_elem.find("sm:priority", SITEMAP_NS)

                urls.append(
                    SitemapURL(
                        loc=loc.text.strip(),
                        lastmod=self._parse_datetime(
                            lastmod_elem.text if lastmod_elem is not None else None
                        ),
                        changefreq=changefreq_elem.text
                        if changefreq_elem is not None
                        else None,
                        priority=float(priority_elem.text)
                        if priority_elem is not None
                        else None,
                    )
                )

        except ET.ParseError as e:
            logger.error(f"Failed to parse URL sitemap: {e}")

        return urls

    async def get_sitemap_urls(
        self,
        sitemap_url: str,
    ) -> list[SitemapURL]:
        """
        Get all URLs from a sitemap.

        Handles both sitemap indices and regular sitemaps.

        Args:
            sitemap_url: URL of the sitemap

        Returns:
            List of SitemapURL objects
        """
        xml_content = await self._fetch_xml(sitemap_url)
        if not xml_content:
            return []

        # Check if it's a sitemap index
        if "<sitemapindex" in xml_content:
            logger.info(f"Processing sitemap index: {sitemap_url}")
            index = self._parse_sitemap_index(xml_content)

            all_urls = []
            for sub_sitemap in index.sitemaps:
                await asyncio.sleep(self.rate_limit)
                sub_urls = await self.get_sitemap_urls(sub_sitemap)
                all_urls.extend(sub_urls)

            return all_urls

        # Regular sitemap
        logger.info(f"Processing sitemap: {sitemap_url}")
        return self._parse_url_sitemap(xml_content)

    async def discover_tax_urls(
        self,
        include_french: bool = True,
        modified_since: datetime | None = None,
    ) -> list[SitemapURL]:
        """
        Discover tax-related URLs from canada.ca sitemaps.

        Args:
            include_french: Include French pages
            modified_since: Only return URLs modified after this date

        Returns:
            List of tax-related SitemapURL objects
        """
        # Known tax-related sitemaps
        sitemaps = [
            "https://www.canada.ca/en/revenue-agency.sitemap.xml",
        ]

        if include_french:
            sitemaps.append("https://www.canada.ca/fr/agence-revenu.sitemap.xml")

        all_urls = []

        for sitemap in sitemaps:
            logger.info(f"Fetching sitemap: {sitemap}")
            urls = await self.get_sitemap_urls(sitemap)
            all_urls.extend(urls)
            await asyncio.sleep(self.rate_limit)

        # Filter to tax-relevant URLs
        tax_patterns = [
            r"/services/taxes",
            r"/services/impots",
            r"/services/e-services",
            r"/programs/.*tax",
            r"/programmes/.*impot",
        ]

        filtered_urls = []
        for url in all_urls:
            # Check if URL matches tax patterns
            if any(re.search(pattern, url.loc, re.I) for pattern in tax_patterns):
                # Check modification date
                if modified_since and url.lastmod:
                    if url.lastmod < modified_since:
                        continue

                filtered_urls.append(url)

        logger.info(f"Found {len(filtered_urls)} tax-related URLs")
        return filtered_urls


class URLFilter:
    """Filter URLs based on patterns."""

    def __init__(
        self,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
    ):
        """
        Initialize URL filter.

        Args:
            include_patterns: URL patterns to include (regex)
            exclude_patterns: URL patterns to exclude (regex)
        """
        self.include_patterns = [
            re.compile(p, re.I) for p in (include_patterns or [])
        ]
        self.exclude_patterns = [
            re.compile(p, re.I)
            for p in (
                exclude_patterns
                or [
                    r"\.pdf$",
                    r"/forms/",
                    r"/formulaires/",
                    r"/search",
                    r"/rechercher",
                    r"my-account",
                    r"mon-dossier",
                    r"#",
                ]
            )
        ]

    def filter(self, urls: list[SitemapURL]) -> list[SitemapURL]:
        """Filter URLs based on patterns."""
        filtered = []

        for url in urls:
            loc = url.loc

            # Check exclusions first
            if any(p.search(loc) for p in self.exclude_patterns):
                continue

            # Check inclusions (if any specified)
            if self.include_patterns:
                if not any(p.search(loc) for p in self.include_patterns):
                    continue

            filtered.append(url)

        return filtered


async def discover_urls_from_sitemap(
    sitemap_url: str,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    modified_since: datetime | None = None,
) -> list[str]:
    """
    Convenience function to discover and filter URLs from a sitemap.

    Args:
        sitemap_url: URL of the sitemap
        include_patterns: URL patterns to include
        exclude_patterns: URL patterns to exclude
        modified_since: Only return URLs modified after this date

    Returns:
        List of filtered URL strings
    """
    async with SitemapParser() as parser:
        urls = await parser.get_sitemap_urls(sitemap_url)

        # Apply date filter
        if modified_since:
            urls = [u for u in urls if u.lastmod is None or u.lastmod >= modified_since]

        # Apply URL pattern filter
        url_filter = URLFilter(include_patterns, exclude_patterns)
        urls = url_filter.filter(urls)

        return [u.loc for u in urls]
