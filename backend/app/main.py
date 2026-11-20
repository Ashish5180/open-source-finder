"""FastAPI application entry point.

Responsibilities:
  - Create and configure the FastAPI application instance.
  - Register middleware (CORS, request-id).
  - Include API routers.
  - Manage application lifecycle (startup/shutdown).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint

from app.api.routes.health import router as health_router
from app.api.routes.opportunities import router as opportunities_router
from app.core.config import get_settings
from app.github.client import GitHubClient
from app.schemas.models import ErrorCode, ErrorResponse
from app.services.discovery import DiscoveryService
from app.storage.database import DatabaseManager
from app.storage.repositories import IssueRepository

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown."""
    settings = get_settings()
    db_manager = DatabaseManager(settings)
    await db_manager.initialize()
    app.state.db_manager = db_manager

    github_client = GitHubClient(settings)
    app.state.github_client = github_client

    repository = IssueRepository(db_manager)
    app.state.repository = repository

    discovery_service = DiscoveryService(
        github_client=github_client, repository=repository
    )
    app.state.discovery_service = discovery_service

    logger.info(
        "Application started",
        extra={
            "version": settings.app_version,
            "database": str(settings.database_path),
            "github_configured": settings.github_token is not None,
        },
    )

    yield

    # Shutdown: close client and database connections
    await github_client.close()
    await db_manager.close()
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
    )

    # ── CORS ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )

    # ── Request ID middleware ────────────────────────────────────────────
    @app.middleware("http")
    async def add_request_id(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Attach a unique request ID to every request for tracing."""
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # ── Global exception handler ─────────────────────────────────────────
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Catch unhandled exceptions and return structured error."""
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception(
            "Unhandled exception",
            extra={"request_id": request_id},
        )
        error = ErrorResponse(
            error_code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected error occurred. Please try again.",
            detail=None,  # Never leak internal details
        )
        return JSONResponse(
            status_code=500,
            content=error.model_dump(),
        )

    # ── Routers ──────────────────────────────────────────────────────────
    app.include_router(health_router)
    app.include_router(opportunities_router)

    return app


app = create_app()
