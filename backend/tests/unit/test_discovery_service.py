"""Unit tests for DiscoveryService orchestration."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
import pytest_asyncio

from app.core.config import Settings
from app.domain.ranking import OpportunityRanker
from app.github.client import GitHubClient
from app.github.query_planner import QueryPlanner
from app.schemas.models import CandidateProfile, ExperienceLevel, SearchRequest
from app.services.discovery import DiscoveryService
from app.storage.database import DatabaseManager
from app.storage.repositories import IssueRepository

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture()
def search_fixture_data() -> dict[str, Any]:
    with open(FIXTURES_DIR / "github_search_issues.json", encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


@pytest.fixture()
def repo_fixture_data() -> dict[str, Any]:
    with open(FIXTURES_DIR / "github_repo_detail.json", encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


@pytest_asyncio.fixture()
async def service_db(tmp_path: Path) -> AsyncGenerator[DatabaseManager, None]:
    settings = Settings(database_path=tmp_path / "service_test.db")
    manager = DatabaseManager(settings)
    await manager.initialize()
    yield manager
    await manager.close()


@pytest.mark.asyncio
class TestDiscoveryService:
    """Test suite for DiscoveryService orchestration."""

    async def test_search_and_rank_end_to_end(
        self,
        service_db: DatabaseManager,
        search_fixture_data: dict[str, Any],
        repo_fixture_data: dict[str, Any],
    ) -> None:
        settings = Settings(github_max_concurrent_requests=3)

        def mock_handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if "search/issues" in path:
                return httpx.Response(200, json=search_fixture_data)
            if "repos/fastapi/fastapi" in path:
                return httpx.Response(200, json=repo_fixture_data)
            return httpx.Response(404, json={"message": "Not found"})

        transport = httpx.MockTransport(mock_handler)
        mock_http = httpx.AsyncClient(transport=transport, base_url="https://api.github.com")

        github_client = GitHubClient(settings, custom_http_client=mock_http)
        repository = IssueRepository(service_db)
        service = DiscoveryService(
            github_client=github_client,
            repository=repository,
            query_planner=QueryPlanner(default_max_pages=1),
            ranker=OpportunityRanker(),
        )

        profile = CandidateProfile(
            languages=["Python"],
            frameworks=["FastAPI"],
            experience=ExperienceLevel.BEGINNER,
            hours_per_week=10.0,
        )
        request = SearchRequest(profile=profile, max_results=10)

        response = await service.search_and_rank(request)

        assert response.total_found > 0
        assert len(response.opportunities) > 0
        assert response.scoring_config_version == "v1.0.0"

        # Verify PR #103 was excluded (Spec target: 0 PRs as issues)
        for opp in response.opportunities:
            assert "103" not in opp.issue_key
            assert len(opp.reasons) >= 1
            assert opp.scores.composite_score >= 0.0

        # Verify issues were persisted to SQLite cache
        cached = await repository.get_issue_by_key("fastapi/fastapi#101")
        assert cached is not None
        assert cached.title == "Add support for custom datetime serializers"

        await github_client.close()
