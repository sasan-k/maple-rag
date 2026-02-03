"""
Job scheduler for background tasks.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger("scheduler")

scheduler = AsyncIOScheduler()


async def scheduled_ingestion_job() -> None:
    """Run incremental ingestion."""
    logger.info("Starting scheduled ingestion job")
    try:
        # Import here to avoid circular dependencies
        import sys
        import os
        
        # Ensure scripts are in path if needed, though we can import module
        # Since incremental_ingest is in scripts/, we need to be careful
        # We'll use subprocess to run it to ensure clean slate and memory isolation
        # Or we can refactor code. 
        # For simplicity and isolation in a long-running web process, subprocess is safer to avoid memory leaks.
        
        import asyncio
        
        # Run generic taxes scrape
        logger.info("Scraping generic taxes...")
        proc1 = await asyncio.create_subprocess_exec(
            sys.executable,
            "scripts/incremental_ingest.py",
            "--filter", "en/services/taxes/",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc1.communicate()
        if proc1.returncode != 0:
            logger.error(f"Ingestion failed: {stderr.decode()}")
        else:
            logger.info("Ingestion (Taxes) completed")
            
        # Run business taxes scrape
        logger.info("Scraping business taxes...")
        proc2 = await asyncio.create_subprocess_exec(
            sys.executable,
            "scripts/incremental_ingest.py",
            "--filter", "en/revenue-agency/services/tax/businesses/",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc2.communicate()
        if proc2.returncode != 0:
            logger.error(f"Ingestion failed: {stderr.decode()}")
        else:
            logger.info("Ingestion (Business) completed")
            
    except Exception as e:
        logger.error(f"Error in scheduled job: {e}")


def start_scheduler() -> None:
    """Start the scheduler."""
    if scheduler.running:
        return

    # Schedule job for 3 AM UTC every day
    scheduler.add_job(
        scheduled_ingestion_job,
        CronTrigger(hour=3, minute=0, timezone="UTC"),
        id="incremental_ingest",
        replace_existing=True,
    )
    
    scheduler.start()
    logger.info("Scheduler started")


def stop_scheduler() -> None:
    """Stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
