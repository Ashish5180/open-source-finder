"""Offline integration tests using recorded GitHub fixtures.

Verifies the complete Phase 2 pipeline without hitting live GitHub APIs:
  - Fixtures load and parse cleanly into normalized domain records.
  - Pull requests are detected and separated (Spec target: 0 PRs as issues).
  - Normalizer deduplicates repeated records.
  - SQLite repository upserts idempotently without duplicate row errors.
  - GitHubClient replays fixtures through MockTransport.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import httpx
import pytest

from app.core.config import Settings
from app.github.client import GitHubClient
from app.github.normalizer import IssueNormalizer
from app.storage.database import DatabaseManager
from app.storage.repositories import IssueRepository

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture()
def search_fixture_data() -> dict[str, Any]:
    fixture_path = FIXTURES_DIR / "github_search_issues.json"
    with open(fixture_path, encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


@pytest.fixture()
def repo_fixture_data() -> dict[str, Any]:
    fixture_path = FIXTURES_DIR / "github_repo_detail.json"
    with open(fixture_path, encoding="utf-8") as f:
        return cast(dict[str, Any], json.load(f))


@pytest.mark.asyncio
class TestFixtureReplayPipeline:
    """Test full ingestion, normalization, and persistence pipeline with fixtures."""

    async def test_search_fixture_parsing_and_pr_separation(
        self, search_fixture_data: dict[str, Any]
    ) -> None:
        items = search_fixture_data["items"]
        assert len(items) == 5

        normalized = [
            issue
            for raw in items
            if (issue := IssueNormalizer.normalize_issue(raw)) is not None
        ]
        assert len(normalized) == 5

        # Check PR detection (number 103 is a PR)
        prs = [i for i in normalized if i.is_pr]
        issues = [i for i in normalized if not i.is_pr]

        assert len(prs) == 1
        assert prs[0].issue_key == "fastapi/fastapi#103"
        assert len(issues) == 4

        # Check assignment detection (number 102 is assigned)
        assigned = [i for i in issues if i.is_assigned]
        assert len(assigned) == 1
        assert assigned[0].issue_key == "fastapi/fastapi#102"

        # Check state parsing (number 201 is closed)
        closed = [i for i in issues if i.state == "closed"]
        assert len(closed) == 1
        assert closed[0].issue_key == "pallets/flask#201"

    async def test_repo_fixture_parsing(self, repo_fixture_data: dict[str, Any]) -> None:
        repo = IssueNormalizer.normalize_repo(repo_fixture_data)
        assert repo is not None
        assert repo.repo_key == "fastapi/fastapi"
        assert repo.stars == 72000
        assert repo.license_spdx == "MIT"
        assert repo.primary_language == "Python"
        assert repo.open_issues_count == 350

    async def test_idempotent_database_caching_from_fixtures(
        self, search_fixture_data: dict[str, Any], tmp_path: Path
    ) -> None:
        db_path = tmp_path / "replay_test.db"
        settings = Settings(database_path=db_path)
        db_manager = DatabaseManager(settings)
        await db_manager.initialize()

        repo = IssueRepository(db_manager)

        items = search_fixture_data["items"]
        normalized = [
            issue
            for raw in items
            if (issue := IssueNormalizer.normalize_issue(raw)) is not None
        ]

        # First ingestion
        count1 = await repo.upsert_issues(normalized, etag='"etag-fixture-1"')
        assert count1 == 5

        # Verify all 5 are in the database
        all_keys = [i.issue_key for i in normalized]
        fetched = await repo.get_issues_by_keys(all_keys)
        assert len(fetched) == 5

        # Replay the identical ingestion (simulating 2nd fetch / refresh)
        count2 = await repo.upsert_issues(normalized, etag='"etag-fixture-2"')
        assert count2 == 5

        # Count must remain exactly 5 (no duplicates created)
        fetched_after = await repo.get_issues_by_keys(all_keys)
        assert len(fetched_after) == 5

        await db_manager.close()

    async def test_client_fixture_mock_transport(
        self, search_fixture_data: dict[str, Any], repo_fixture_data: dict[str, Any]
    ) -> None:
        """Simulate GitHubClient calling mocked GitHub API using recorded fixtures."""
        settings = Settings(github_max_concurrent_requests=5)

        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if "search/issues" in path:
                return httpx.Response(
                    200,
                    json=search_fixture_data,
                    headers={
                        "etag": '"search-etag-999"',
                        "x-ratelimit-remaining": "4850",
                        "x-ratelimit-limit": "5000",
                    },
                )
            if "repos/fastapi/fastapi" in path:
                return httpx.Response(
                    200,
                    json=repo_fixture_data,
                    headers={"etag": '"repo-etag-999"'},
                )
            return httpx.Response(404, json={"message": "Not found"})

        transport = httpx.MockTransport(handler)
        mock_http = httpx.AsyncClient(transport=transport, base_url="https://api.github.com")

        client = GitHubClient(settings, custom_http_client=mock_http)

        items, total, etag = await client.search_issues("is:issue is:open")
        assert total == 5
        assert len(items) == 5
        assert etag == '"search-etag-999"'
        assert client.rate_tracker.remaining == 4850

        repo_dict, repo_etag, _ = await client.get_repo("fastapi", "fastapi")
        assert repo_dict is not None
        assert repo_dict["full_name"] == "fastapi/fastapi"
        assert repo_etag == '"repo-etag-999"'

        await client.close()
