"""SQLite database lifecycle manager.

Responsibilities:
  - Create the database file and directory if needed.
  - Enable WAL mode and configure busy_timeout on initialization.
  - Provide async engine access for the repository layer.
  - Health check connectivity.
  - Clean shutdown.

Design rules (from spec Section 8):
  - Enable WAL mode for concurrent read access.
  - Configure finite busy_timeout to avoid indefinite blocking.
  - Never hold a database transaction open during network I/O.
  - Keep write transactions short.
  - Use unique constraints to prevent duplicate rows.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.storage.models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages the SQLite async engine lifecycle."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def initialize(self) -> None:
        """Create the database, enable WAL mode, and set busy_timeout."""
        db_path = self._settings.database_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

        db_url = f"sqlite+aiosqlite:///{db_path}"

        self._engine = create_async_engine(
            db_url,
            echo=self._settings.debug,
            pool_pre_ping=True,
        )

        # Configure WAL mode and busy_timeout via connection event
        @event.listens_for(self._engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection: Any, _: Any) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute(
                f"PRAGMA busy_timeout={self._settings.database_busy_timeout_ms}"
            )
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        self._session_factory = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
        )

        # Create tables on schema initialization
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info(
            "Database initialized",
            extra={
                "path": str(db_path),
                "wal_mode": True,
                "busy_timeout_ms": self._settings.database_busy_timeout_ms,
            },
        )

    async def is_connected(self) -> bool:
        """Check database connectivity with a simple query."""
        if self._engine is None:
            return False
        try:
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:
            logger.exception("Database connectivity check failed")
            return False

    def get_session(self) -> AsyncSession:
        """Create a new async session for a unit of work."""
        if self._session_factory is None:
            msg = "Database not initialized. Call initialize() first."
            raise RuntimeError(msg)
        return self._session_factory()

    @property
    def engine(self) -> AsyncEngine:
        """Access the underlying engine (for table creation, etc.)."""
        if self._engine is None:
            msg = "Database not initialized. Call initialize() first."
            raise RuntimeError(msg)
        return self._engine

    async def close(self) -> None:
        """Dispose of the engine and release connections."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("Database connections closed")
