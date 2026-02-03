#!/usr/bin/env python
"""
Database initialization script.

Creates the database schema and enables required extensions.
Works with both local PostgreSQL and AWS Aurora.

Usage:
    uv run python scripts/init_db.py
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()


async def init_database():
    """Initialize the database schema."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from src.config.settings import get_settings
    from src.db.models import Base

    settings = get_settings()

    # Mask password for display
    db_url = settings.database_url
    if "@" in db_url:
        parts = db_url.split("@")
        masked = parts[0].rsplit(":", 1)[0] + ":****@" + parts[1]
    else:
        masked = db_url

    print("=" * 60)
    print("Database Initialization")
    print("=" * 60)
    print(f"\nConnecting to: {masked}")

    try:
        engine = create_async_engine(settings.database_url, echo=False)

        async with engine.connect() as conn:
            # Check PostgreSQL version
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            print("\n[OK] Connected to PostgreSQL")
            print(f"    Version: {version[:60]}...")

            # Enable pgvector extension
            print("\n[INFO] Enabling pgvector extension...")
            try:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                await conn.commit()
                print("[OK] pgvector extension enabled")
            except Exception as e:
                print(f"[WARN] Could not enable pgvector: {e}")
                print("       You may need to run: CREATE EXTENSION vector; as superuser")

        # Create schema
        print("\n[INFO] Creating database schema...")

        async with engine.begin() as conn:
            # Create schema if not exists
            await conn.execute(text("CREATE SCHEMA IF NOT EXISTS canadaca"))

            # Create all tables
            await conn.run_sync(Base.metadata.create_all)

        print("[OK] Database schema created")

        # Verify tables
        async with engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'canadaca'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]

            print("\n[INFO] Created tables in 'canadaca' schema:")
            for table in tables:
                print(f"    - {table}")

        await engine.dispose()

        print("\n" + "=" * 60)
        print("[SUCCESS] Database initialization complete!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n[FAIL] Database initialization failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Check your DATABASE_URL in .env")
        print("  2. Ensure the database server is running")
        print("  3. Verify your credentials")
        print("  4. For AWS Aurora, ensure your IP is allowed in the security group")
        return False


async def verify_pgvector():
    """Verify pgvector is working correctly."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from src.config.settings import get_settings

    settings = get_settings()

    print("\n" + "=" * 60)
    print("Verifying pgvector")
    print("=" * 60)

    try:
        engine = create_async_engine(settings.database_url, echo=False)

        async with engine.connect() as conn:
            # Test vector operations
            result = await conn.execute(text("""
                SELECT '[1,2,3]'::vector <-> '[4,5,6]'::vector as distance
            """))
            distance = result.scalar()
            print(f"\n[OK] Vector distance calculation works: {distance}")

            # Check vector dimension support
            result = await conn.execute(text("""
                SELECT '[1,2,3,4,5]'::vector(5) as vec
            """))
            print("[OK] Vector with dimension constraint works")

        await engine.dispose()
        return True

    except Exception as e:
        print(f"[FAIL] pgvector verification failed: {e}")
        return False


async def main():
    success = await init_database()

    if success:
        await verify_pgvector()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
