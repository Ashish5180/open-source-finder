"""Health check endpoint.

Returns application health status including:
  - Backend status
  - Database connectivity
  - GitHub API configuration (presence, not the token value)
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from app.core.config import get_settings
from app.schemas.models import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Backend and storage health check",
    description="Returns health status. Never exposes secrets.",
)
async def health_check(request: Request) -> HealthResponse:
    """Check backend health, database connectivity, and config status."""
    settings = get_settings()

    # Check database connectivity
    db_connected = False
    try:
        db_manager = request.app.state.db_manager
        db_connected = await db_manager.is_connected()
    except Exception:
        logger.warning(
            "Database health check failed",
            extra={"request_id": getattr(request.state, "request_id", "unknown")},
        )

    return HealthResponse(
        status="ok" if db_connected else "degraded",
        version=settings.app_version,
        database_connected=db_connected,
        github_api_configured=settings.github_token is not None,
    )
