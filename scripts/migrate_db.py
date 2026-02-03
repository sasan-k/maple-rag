#!/usr/bin/env python
"""
Database migration script.

Creates or updates the database schema.

Usage:
    python scripts/migrate_db.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.logging import get_logger, setup_logging
from src.db.connection import close_db, get_engine
from src.db.models import Base

logger = get_logger("scripts.migrate")


async def run_migrations():
    """Run database migrations."""
    logger.info("Starting database migrations...")

    engine = get_engine()

    async with engine.begin() as conn:
        # Create pgvector extension
        logger.info("Creating pgvector extension...")
        try:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        except Exception as e:
            logger.warning(f"Could not create vector extension: {e}")

        # Create schema
        logger.info("Creating canadaca schema...")
        try:
            await conn.execute("CREATE SCHEMA IF NOT EXISTS canadaca")
        except Exception as e:
            logger.warning(f"Could not create schema: {e}")

        # Create tables
        logger.info("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Migrations complete!")

    # Close connection
    await close_db()


def main():
    """Main entry point."""
    setup_logging()
    asyncio.run(run_migrations())


if __name__ == "__main__":
    main()
