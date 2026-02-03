#!/usr/bin/env python
"""
Test script to scrape and process canada.ca tax pages.

Usage:
    uv run python scripts/test_scraping.py

This script tests the scraping and embedding pipeline without database storage.
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()


# Sample tax URLs to scrape
TEST_URLS = [
    "https://www.canada.ca/en/services/taxes.html",
    "https://www.canada.ca/en/services/taxes/income-tax.html",
    "https://www.canada.ca/en/revenue-agency/services/tax/individuals/topics/about-your-tax-return.html",
]


async def test_scraping():
    """Test the web crawler."""
    print("=" * 60)
    print("Testing Web Scraper")
    print("=" * 60)

    from src.scraper.crawler import CanadaCrawler

    crawler = CanadaCrawler(base_urls=TEST_URLS[:2], rate_limit=1.0)

    pages = []
    print(f"\n[INFO] Crawling {len(TEST_URLS[:2])} URLs...")

    async for page in crawler.crawl():
        pages.append(page)
        print(f"\n[OK] Scraped: {page.url}")
        print(
            f"    Title: {page.title[:60]}..."
            if len(page.title) > 60
            else f"    Title: {page.title}"
        )
        print(f"    Language: {page.language}")
        print(f"    Content length: {len(page.content)} chars")
        print(f"    Word count: ~{page.word_count} words")

    print(f"\n[SUMMARY] Successfully scraped {len(pages)} pages")
    return pages


def test_chunking(pages):
    """Test the content chunker."""
    print("\n" + "=" * 60)
    print("Testing Content Chunker")
    print("=" * 60)

    from src.config.settings import get_settings
    from src.scraper.chunker import ContentChunker

    settings = get_settings()
    chunker = ContentChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    all_chunks = []

    for page in pages:
        chunks = chunker.chunk_document(
            content=page.content,
            url=page.url,
            title=page.title,
            language=page.language,
        )
        all_chunks.extend(chunks)
        print(
            f"\n[OK] Chunked '{page.title[:40]}...' "
            if len(page.title) > 40
            else f"\n[OK] Chunked '{page.title}'"
        )
        print(f"    Created {len(chunks)} chunks")

        # Show first chunk preview
        if chunks:
            preview = chunks[0].content[:150].replace("\n", " ")
            print(f"    First chunk preview: {preview}...")

    print(f"\n[SUMMARY] Created {len(all_chunks)} total chunks from {len(pages)} pages")
    return all_chunks


async def test_embeddings(chunks):
    """Test embedding generation."""
    print("\n" + "=" * 60)
    print("Testing Embedding Generation (AWS Bedrock Titan)")
    print("=" * 60)

    from src.config.settings import get_settings
    from src.llm.factory import EmbeddingFactory

    settings = get_settings()
    print(f"\n[INFO] Using embedding model: {settings.aws_bedrock_embedding_model_id}")
    print(f"[INFO] Expected dimensions: {settings.embedding_dimensions}")

    # Create embeddings
    embeddings = EmbeddingFactory.create_embeddings()

    # Test with first 3 chunks
    test_chunks = chunks[:3]
    texts = [c.content for c in test_chunks]

    print(f"\n[INFO] Generating embeddings for {len(texts)} chunks...")

    try:
        vectors = embeddings.embed_documents(texts)

        print(f"[OK] Generated {len(vectors)} embeddings")
        print(f"    Vector dimensions: {len(vectors[0])}")
        print(f"    Sample vector (first 5 values): {vectors[0][:5]}")

        # Test query embedding
        query = "How do I file my income tax return?"
        query_vector = embeddings.embed_query(query)
        print("\n[OK] Query embedding generated")
        print(f"    Query: '{query}'")
        print(f"    Vector dimensions: {len(query_vector)}")

        return vectors

    except Exception as e:
        print(f"[FAIL] Error generating embeddings: {e}")
        return None


async def test_chat_with_context(chunks):
    """Test chat with scraped context."""
    print("\n" + "=" * 60)
    print("Testing Chat with Scraped Context")
    print("=" * 60)

    from src.llm.factory import LLMFactory

    llm = LLMFactory.create_chat_model()

    # Use first few chunks as context
    context = "\n\n".join([c.content for c in chunks[:3]])

    question = "What services are available for income tax on canada.ca?"

    prompt = f"""You are a helpful Canadian government assistant. Answer the question based on the following context from canada.ca.

Context:
{context}

Question: {question}

Answer in a helpful, concise way. If the context doesn't contain enough information, say so."""

    print(f"\n[INFO] Question: {question}")
    print("[INFO] Generating response...")

    try:
        response = llm.invoke(prompt)
        print("\n[OK] Response generated!\n")
        print("-" * 40)
        print(response.content)
        print("-" * 40)
        return True
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        return False


async def main():
    print("\n" + "=" * 60)
    print("Canada.ca Scraping & Embedding Test")
    print("=" * 60)

    # Test 1: Scraping
    pages = await test_scraping()
    if not pages:
        print("\n[FAIL] No pages scraped, stopping.")
        return 1

    # Test 2: Chunking
    chunks = test_chunking(pages)
    if not chunks:
        print("\n[FAIL] No chunks created, stopping.")
        return 1

    # Test 3: Embeddings
    await test_embeddings(chunks)

    # Test 4: Chat with context
    await test_chat_with_context(chunks)

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
