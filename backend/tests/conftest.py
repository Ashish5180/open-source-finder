"""Shared test fixtures for the backend test suite.

Provides:
  - Temporary database paths (isolated per test)
  - Pre-configured Settings instances
  - FastAPI TestClient with database lifecycle
  - Sample data factories
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from pydantic import HttpUrl

from app.core.config import Settings
from app.schemas.models import (
    CandidateProfile,
    Eligibility,
    ExperienceLevel,
    Opportunity,
    ScoreBreakdown,
)
from app.storage.database import DatabaseManager


@pytest.fixture()
def test_settings(tmp_path: Path) -> Settings:
    """Settings configured for testing with an isolated temp database."""
    return Settings(
        debug=True,
        database_path=tmp_path / "test.db",
        database_busy_timeout_ms=1000,
        github_token=None,
        cors_allowed_origins=["http://localhost:3000"],
    )


@pytest_asyncio.fixture()
async def db_manager(test_settings: Settings) -> AsyncGenerator[DatabaseManager, None]:
    """Initialized database manager for tests, cleaned up after."""
    manager = DatabaseManager(test_settings)
    await manager.initialize()
    yield manager
    await manager.close()


@pytest_asyncio.fixture()
async def async_client(test_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client wired to the FastAPI app with test database."""
    # Import here to avoid circular imports and to use test settings
    from unittest.mock import patch

    from app.core.config import get_settings

    # Clear the lru_cache so we inject test settings
    get_settings.cache_clear()

    with patch("app.core.config.get_settings", return_value=test_settings):
        from app.main import create_app

        app = create_app()

        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                yield client

    # Clean up the cache
    get_settings.cache_clear()


@pytest.fixture()
def sample_profile() -> CandidateProfile:
    """A sample candidate profile for tests."""
    return CandidateProfile(
        languages=["Python", "TypeScript"],
        frameworks=["FastAPI", "React"],
        topics=["web", "cli"],
        experience=ExperienceLevel.INTERMEDIATE,
        hours_per_week=10.0,
        max_setup_hours=3.0,
    )


@pytest.fixture()
def sample_opportunity() -> Opportunity:
    """A sample opportunity for tests."""
    return Opportunity(
        issue_key="facebook/react#12345",
        github_issue_id=100001,
        url=HttpUrl("https://github.com/facebook/react/issues/12345"),
        title="Fix useEffect cleanup in concurrent mode",
        repository="facebook/react",
        labels=["bug", "good first issue"],
        language="TypeScript",
        state="open",
        is_assigned=False,
        has_linked_pr=False,
        created_at=datetime(2024, 3, 1, tzinfo=UTC),
        updated_at=datetime(2024, 6, 15, tzinfo=UTC),
        observed_at=datetime(2024, 6, 20, tzinfo=UTC),
        scores=ScoreBreakdown(
            fit_score=0.85,
            actionability_score=0.7,
            health_score=0.9,
            freshness_score=0.8,
            composite_score=0.81,
        ),
        eligibility=Eligibility.ELIGIBLE,
        reasons=[
            "Language match: TypeScript",
            "Framework match: React",
            "Recent maintainer activity (< 7 days)",
        ],
        uncertainties=["Assignment status based on partial timeline data"],
        scoring_config_version="v1.0.0",
    )
