"""
Health check endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import HealthCheck, ReadinessCheck
from src.db.connection import get_db_session

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthCheck,
    summary="Health check",
    description="Basic health check endpoint",
)
async def health() -> HealthCheck:
    """Check if the service is running."""
    return HealthCheck(status="healthy", version="0.1.0")


@router.get(
    "/ready",
    response_model=ReadinessCheck,
    summary="Readiness check",
    description="Check if the service is ready to handle requests",
)
async def ready(
    db: AsyncSession = Depends(get_db_session),
) -> ReadinessCheck:
    """
    Check if the service is ready.

    Verifies database connectivity.
    """
    checks: dict[str, str] = {}

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)[:50]}"

    # Determine overall status
    all_healthy = all(v == "healthy" for v in checks.values())
    status = "ready" if all_healthy else "not_ready"

    return ReadinessCheck(status=status, checks=checks)
