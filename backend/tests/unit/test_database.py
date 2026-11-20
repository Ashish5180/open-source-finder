"""Tests for the DatabaseManager lifecycle.

Tests cover:
  - Database file creation in nested directories
  - WAL mode is enabled
  - busy_timeout is configured
  - foreign_keys pragma is ON
  - is_connected() returns True after init, False after close
  - get_session() raises before init
  - Double close is safe
  - Engine access raises before init
"""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.core.config import Settings
from app.storage.database import DatabaseManager


@pytest.fixture()
def db_settings(tmp_path: Path) -> Settings:
    """Settings with a temporary database path."""
    return Settings(
        database_path=tmp_path / "sub" / "dir" / "test.db",
        database_busy_timeout_ms=2000,
    )


@pytest_asyncio.fixture()
async def manager(db_settings: Settings) -> DatabaseManager:
    """A fresh DatabaseManager (not yet initialized)."""
    return DatabaseManager(db_settings)


@pytest.mark.asyncio
class TestDatabaseInitialization:
    """Tests for database creation and pragma configuration."""

    async def test_creates_database_file(
        self, manager: DatabaseManager, db_settings: Settings
    ) -> None:
        await manager.initialize()
        assert db_settings.database_path.exists()
        await manager.close()

    async def test_creates_parent_directories(
        self, manager: DatabaseManager, db_settings: Settings
    ) -> None:
        await manager.initialize()
        assert db_settings.database_path.parent.is_dir()
        await manager.close()

    async def test_wal_mode_enabled(self, manager: DatabaseManager) -> None:
        await manager.initialize()
        async with manager.engine.connect() as conn:
            result = await conn.execute(text("PRAGMA journal_mode"))
            mode = result.scalar()
            assert mode == "wal"
        await manager.close()

    async def test_busy_timeout_set(self, manager: DatabaseManager) -> None:
        await manager.initialize()
        async with manager.engine.connect() as conn:
            result = await conn.execute(text("PRAGMA busy_timeout"))
            timeout = result.scalar()
            assert timeout == 2000
        await manager.close()

    async def test_foreign_keys_enabled(self, manager: DatabaseManager) -> None:
        await manager.initialize()
        async with manager.engine.connect() as conn:
            result = await conn.execute(text("PRAGMA foreign_keys"))
            fk = result.scalar()
            assert fk == 1
        await manager.close()


@pytest.mark.asyncio
class TestDatabaseConnectivity:
    """Tests for health check and session management."""

    async def test_is_connected_after_init(self, manager: DatabaseManager) -> None:
        await manager.initialize()
        assert await manager.is_connected() is True
        await manager.close()

    async def test_is_connected_before_init(self, manager: DatabaseManager) -> None:
        assert await manager.is_connected() is False

    async def test_is_connected_after_close(self, manager: DatabaseManager) -> None:
        await manager.initialize()
        await manager.close()
        assert await manager.is_connected() is False

    async def test_get_session_after_init(self, manager: DatabaseManager) -> None:
        await manager.initialize()
        session = manager.get_session()
        assert session is not None
        await session.close()
        await manager.close()

    async def test_get_session_before_init_raises(self, manager: DatabaseManager) -> None:
        with pytest.raises(RuntimeError, match="not initialized"):
            manager.get_session()

    async def test_engine_before_init_raises(self, manager: DatabaseManager) -> None:
        with pytest.raises(RuntimeError, match="not initialized"):
            _ = manager.engine

    async def test_double_close_is_safe(self, manager: DatabaseManager) -> None:
        await manager.initialize()
        await manager.close()
        await manager.close()  # Should not raise
