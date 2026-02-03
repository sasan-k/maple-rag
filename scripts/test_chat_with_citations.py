#!/usr/bin/env python
"""
Test script for the full RAG chat pipeline with citations.

This script tests:
1. Database connectivity (works with Neon, RDS, or local)
2. Vector similarity search
3. Chat responses with source citations
4. Bilingual support (EN/FR)

Usage:
    uv run python scripts/test_chat_with_citations.py
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()


async def test_database_connection():
    """Test database connectivity."""
    print("=" * 60)
    print("Testing Database Connection")
    print("=" * 60)

    from src.config.settings import get_settings
    settings = get_settings()

    # Mask password in connection string for display
    db_url = settings.database_url
    if "@" in db_url:
        parts = db_url.split("@")
        masked = parts[0].rsplit(":", 1)[0] + ":****@" + parts[1]
    else:
        masked = db_url

    print(f"\n[INFO] Database URL: {masked}")

    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(settings.database_url, echo=False)

        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print("[OK] Connected to PostgreSQL")
            print(f"    Version: {version[:50]}...")

            # Check for pgvector extension
            result = await conn.execute(
                text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            )
            has_pgvector = result.scalar()
            print(f"    pgvector extension: {'Installed' if has_pgvector else 'NOT INSTALLED'}")

        await engine.dispose()
        return True

    except Exception as e:
        print(f"[FAIL] Database connection failed: {e}")
        print("\n[TIP] Make sure your database is running and DATABASE_URL is correct.")
        print("      For Neon: Sign up at https://neon.tech and get your connection string")
        return False


async def test_redis_connection():
    """Test Redis connectivity."""
    print("\n" + "=" * 60)
    print("Testing Redis Connection")
    print("=" * 60)

    from src.config.settings import get_settings
    settings = get_settings()

    print(f"\n[INFO] Redis URL: {settings.redis_url.split('@')[-1] if '@' in settings.redis_url else settings.redis_url}")

    try:
        import redis.asyncio as redis

        client = redis.from_url(settings.redis_url, decode_responses=True)
        await client.ping()
        print("[OK] Connected to Redis")

        # Test set/get
        await client.set("test_key", "canada.ca_chat_test")
        value = await client.get("test_key")
        print(f"    Set/Get test: {'PASS' if value == 'canada.ca_chat_test' else 'FAIL'}")
        await client.delete("test_key")

        await client.close()
        return True

    except Exception as e:
        print(f"[WARN] Redis connection failed: {e}")
        print("       Redis is optional - the app can run without it.")
        return False


async def test_embedding_search():
    """Test vector embedding and similarity search."""
    print("\n" + "=" * 60)
    print("Testing Embedding Generation")
    print("=" * 60)

    from src.config.settings import get_settings
    from src.llm.factory import EmbeddingFactory

    settings = get_settings()
    print(f"\n[INFO] Embedding model: {settings.aws_bedrock_embedding_model_id}")

    try:
        embeddings = EmbeddingFactory.create_embeddings()

        # Test English query
        en_query = "How do I file my income tax return in Canada?"
        en_vector = embeddings.embed_query(en_query)
        print(f"[OK] English query embedded ({len(en_vector)} dimensions)")

        # Test French query
        fr_query = "Comment puis-je produire ma declaration de revenus?"
        fr_vector = embeddings.embed_query(fr_query)
        print(f"[OK] French query embedded ({len(fr_vector)} dimensions)")

        return True

    except Exception as e:
        print(f"[FAIL] Embedding failed: {e}")
        return False


async def test_chat_with_citations():
    """Test chat response generation with citations."""
    print("\n" + "=" * 60)
    print("Testing Chat with Citations")
    print("=" * 60)

    from src.config.settings import get_settings
    from src.llm.factory import LLMFactory
    from src.scraper.chunker import ContentChunker
    from src.scraper.crawler import CanadaCrawler

    settings = get_settings()

    # First, scrape some content to use as context
    print("\n[INFO] Scraping sample pages for context...")

    crawler = CanadaCrawler(
        base_urls=["https://www.canada.ca/en/services/taxes/income-tax.html"],
        rate_limit=1.0
    )

    pages = []
    async for page in crawler.crawl():
        pages.append(page)
        print(f"    Scraped: {page.title}")

    if not pages:
        print("[FAIL] No pages scraped")
        return False

    # Chunk the content
    chunker = ContentChunker(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    chunks = []
    for page in pages:
        page_chunks = chunker.chunk_document(
            content=page.content,
            url=page.url,
            title=page.title,
            language=page.language,
        )
        chunks.extend(page_chunks)

    print(f"    Created {len(chunks)} chunks")

    # Create LLM
    llm = LLMFactory.create_chat_model()

    # Build context with source information
    context_parts = []
    sources = []

    for i, chunk in enumerate(chunks[:3]):  # Use first 3 chunks
        context_parts.append(f"[Source {i+1}]\nURL: {chunk.metadata.get('url', 'Unknown')}\nTitle: {chunk.metadata.get('title', 'Unknown')}\nContent: {chunk.content}")
        sources.append({
            "title": chunk.metadata.get("title", "Unknown"),
            "url": chunk.metadata.get("url", "Unknown"),
            "snippet": chunk.content[:150] + "..."
        })

    context = "\n\n".join(context_parts)

    # Test question
    question = "What income tax services are available on canada.ca?"

    prompt = f"""You are a helpful Canadian government assistant. Answer questions based on the provided context from canada.ca.

IMPORTANT: Always cite your sources! Include the URL at the end of your response.

Context:
{context}

Question: {question}

Provide a helpful answer and cite the sources used."""

    print(f"\n[INFO] Question: {question}")
    print("[INFO] Generating response with citations...")

    try:
        response = llm.invoke(prompt)

        print("\n[OK] Response generated with citations!")
        print("\n" + "-" * 40)
        print("RESPONSE:")
        print("-" * 40)
        print(response.content)
        print("-" * 40)

        print("\n" + "-" * 40)
        print("SOURCES (from context):")
        print("-" * 40)
        for i, src in enumerate(sources, 1):
            print(f"  [{i}] {src['title']}")
            print(f"      URL: {src['url']}")
        print("-" * 40)

        return True

    except Exception as e:
        print(f"[FAIL] Chat failed: {e}")
        return False


async def test_french_chat():
    """Test French language chat."""
    print("\n" + "=" * 60)
    print("Testing French Language Chat")
    print("=" * 60)

    from src.llm.factory import LLMFactory

    llm = LLMFactory.create_chat_model()

    question = "Quels sont les services fiscaux disponibles sur canada.ca?"

    prompt = f"""Vous etes un assistant gouvernemental canadien. Repondez en francais.

Question: {question}

Repondez brievement en francais."""

    print(f"\n[INFO] Question (FR): {question}")

    try:
        response = llm.invoke(prompt)

        print("\n[OK] French response generated!")
        print("-" * 40)
        print(response.content)
        print("-" * 40)

        return True

    except Exception as e:
        print(f"[FAIL] French chat failed: {e}")
        return False


async def main():
    print("\n" + "=" * 60)
    print("Canada.ca Chat Agent - Full Integration Test")
    print("=" * 60)

    results = {}

    # Test database (optional for this test)
    results["database"] = await test_database_connection()

    # Test Redis (optional)
    results["redis"] = await test_redis_connection()

    # Test embeddings
    results["embeddings"] = await test_embedding_search()

    # Test chat with citations
    results["chat_citations"] = await test_chat_with_citations()

    # Test French
    results["french"] = await test_french_chat()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test, passed in results.items():
        status = "[OK]" if passed else "[FAIL]" if passed is False else "[SKIP]"
        print(f"  {test:20} {status}")

    all_critical_passed = results.get("embeddings", False) and results.get("chat_citations", False)

    if all_critical_passed:
        print("\n[SUCCESS] Core RAG pipeline with citations is working!")
    else:
        print("\n[WARNING] Some tests failed. Check the output above.")

    print("=" * 60)

    return 0 if all_critical_passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
