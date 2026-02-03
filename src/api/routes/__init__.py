"""API routes module."""

from src.api.routes.admin import router as admin_router
from src.api.routes.chat import router as chat_router
from src.api.routes.health import router as health_router

__all__ = ["health_router", "chat_router", "admin_router"]
