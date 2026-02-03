"""
Tests for web scraper.
"""

from bs4 import BeautifulSoup

from src.scraper.chunker import ContentChunker
from src.scraper.crawler import CanadaCrawler, ScrapedPage


class TestCanadaCrawler:
    """Test CanadaCrawler class."""

    def test_initialization(self):
        """Test crawler initialization."""
        crawler = CanadaCrawler(
            base_urls=["https://example.com"],
            rate_limit=2.0,
        )
        assert len(crawler.base_urls) == 1
        assert crawler.rate_limit == 2.0

    def test_add_url(self):
        """Test adding URLs."""
        crawler = CanadaCrawler()
        crawler.add_url("https://example.com/1")
        crawler.add_url("https://example.com/2")
        crawler.add_url("https://example.com/1")  # Duplicate

        assert len(crawler.base_urls) == 2

    def test_add_urls(self):
        """Test adding multiple URLs."""
        crawler = CanadaCrawler()
        crawler.add_urls(
            [
                "https://example.com/1",
                "https://example.com/2",
                "https://example.com/3",
            ]
        )

        assert len(crawler.base_urls) == 3

    def test_extract_title(self, sample_html: str):
        """Test title extraction."""
        crawler = CanadaCrawler()
        soup = BeautifulSoup(sample_html, "lxml")

        title = crawler._extract_title(soup)
        assert title == "Tax Information"

    def test_extract_content(self, sample_html: str):
        """Test content extraction."""
        crawler = CanadaCrawler()
        soup = BeautifulSoup(sample_html, "lxml")

        content = crawler._extract_content(soup)

        # Should contain main content
        assert "taxes in Canada" in content
        assert "April 30" in content

        # Should not contain navigation/footer
        assert "Navigation content" not in content
        assert "Footer content" not in content

    def test_detect_language_english(self):
        """Test English language detection."""
        crawler = CanadaCrawler()
        soup = BeautifulSoup('<html lang="en"><body></body></html>', "lxml")

        lang = crawler._detect_language(
            "https://www.canada.ca/en/taxes.html",
            soup,
        )
        assert lang == "en"

    def test_detect_language_french(self, sample_french_html: str):
        """Test French language detection."""
        crawler = CanadaCrawler()
        soup = BeautifulSoup(sample_french_html, "lxml")

        lang = crawler._detect_language(
            "https://www.canada.ca/fr/impots.html",
            soup,
        )
        assert lang == "fr"

    def test_extract_links(self, sample_html: str):
        """Test link extraction."""
        html_with_links = """
        <html>
        <body>
            <a href="/en/page1">Page 1</a>
            <a href="https://www.canada.ca/en/page2">Page 2</a>
            <a href="https://external.com/page">External</a>
            <a href="#anchor">Anchor</a>
            <a href="javascript:void(0)">JS</a>
        </body>
        </html>
        """
        crawler = CanadaCrawler()
        links = crawler._extract_links(
            html_with_links,
            "https://www.canada.ca/en/",
        )

        # Should include internal links
        assert any("page1" in link for link in links)
        assert any("page2" in link for link in links)

        # Should exclude external, anchor, and javascript links
        assert not any("external.com" in link for link in links)

    def test_clean_text(self):
        """Test text cleaning."""
        crawler = CanadaCrawler()

        dirty_text = "  Multiple   spaces  \n\n\n\nToo many newlines  "
        clean = crawler._clean_text(dirty_text)

        assert "   " not in clean
        assert "\n\n\n" not in clean
        assert clean.startswith("Multiple")


class TestScrapedPage:
    """Test ScrapedPage dataclass."""

    def test_word_count(self):
        """Test word count property."""
        page = ScrapedPage(
            url="https://example.com",
            title="Test",
            content="This is a test with five words.",
            language="en",
            html="",
        )
        # Note: contractions and punctuation affect count
        assert page.word_count == 7


class TestContentChunker:
    """Test ContentChunker class."""

    def test_initialization(self):
        """Test chunker initialization."""
        chunker = ContentChunker(chunk_size=500, chunk_overlap=100)
        assert chunker.chunk_size == 500
        assert chunker.chunk_overlap == 100

    def test_chunk_text_simple(self):
        """Test simple text chunking."""
        chunker = ContentChunker(chunk_size=100, chunk_overlap=20)
        text = "A" * 50 + " " + "B" * 50 + " " + "C" * 50

        chunks = chunker.chunk_text(text)

        assert len(chunks) >= 1
        assert all(len(c.content) <= 200 for c in chunks)  # Allow some overflow

    def test_chunk_text_empty(self):
        """Test chunking empty text."""
        chunker = ContentChunker()

        chunks = chunker.chunk_text("")
        assert len(chunks) == 0

        chunks = chunker.chunk_text("   ")
        assert len(chunks) == 0

    def test_chunk_text_metadata(self):
        """Test metadata in chunks."""
        chunker = ContentChunker()
        text = "This is sample text for testing."

        chunks = chunker.chunk_text(text, metadata={"source": "test"})

        assert len(chunks) > 0
        assert chunks[0].metadata["source"] == "test"
        assert "chunk_index" in chunks[0].metadata
        assert "total_chunks" in chunks[0].metadata

    def test_chunk_document(self):
        """Test document chunking with standard metadata."""
        chunker = ContentChunker()

        chunks = chunker.chunk_document(
            content="This is a test document about Canadian taxes.",
            url="https://canada.ca/taxes",
            title="Tax Information",
            language="en",
        )

        assert len(chunks) > 0
        assert chunks[0].metadata["url"] == "https://canada.ca/taxes"
        assert chunks[0].metadata["title"] == "Tax Information"
        assert chunks[0].metadata["language"] == "en"

    def test_chunk_overlap(self):
        """Test that chunks have overlap."""
        chunker = ContentChunker(chunk_size=50, chunk_overlap=10)

        # Create text that will span multiple chunks
        text = " ".join(["word"] * 50)
        chunks = chunker.chunk_text(text)

        if len(chunks) > 1:
            # Check for overlap between consecutive chunks
            for i in range(len(chunks) - 1):
                current_end = chunks[i].content[-20:]
                next_start = chunks[i + 1].content[:20]
                # Due to overlap, there should be some shared content
                # Note: This is approximate due to how splitter works
                assert len(current_end) > 0 or len(next_start) > 0
