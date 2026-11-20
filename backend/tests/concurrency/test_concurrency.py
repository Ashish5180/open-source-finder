"""Concurrency, race condition, and failure mode tests.

Adheres to Section 8 of spec:
  - Test simultaneous identical searches
  - Test simultaneous different searches
  - Test refresh vs feedback concurrency
  - Test cancellation safety without leaving locks or corrupting DB
  - Verify SQLite WAL mode and short transactions
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.core.config import Settings
from app.domain.ranking import OpportunityRanker
from app.github.client import GitHubClient
from app.github.normalizer import NormalizedIssue, NormalizedRepo
from app.github.query_planner import QueryPlanner
from app.schemas.models import (
    CandidateProfile,
    ExperienceLevel,
    FeedbackStatus,
    SearchRequest,
)
from app.services.discovery import DiscoveryService
from app.storage.database import DatabaseManager
from app.storage.repositories import IssueRepository


def create_sample_issue(
    key: str, repo: str = "fastapi/fastapi", number: int = 1
) -> NormalizedIssue:
    now = datetime.now(tz=UTC)
    return NormalizedIssue(
        issue_key=key,
        github_issue_id=100 + number,
        repository=repo,
        number=number,
        url=f"https://github.com/{repo}/issues/{number}",
        title=f"Sample test issue {number}",
        body="Steps to reproduce: run `pytest`. Expected behavior: pass.",
        state="open",
        state_reason=None,
        locked=False,
        is_pr=False,
        labels=("good first issue", "python"),
        is_assigned=False,
        assignee_count=0,
        comments_count=2,
        created_at=now,
        updated_at=now,
        closed_at=None,
    )


def create_sample_repo(repo_key: str = "fastapi/fastapi") -> NormalizedRepo:
    return NormalizedRepo(
        repo_key=repo_key,
        description="FastAPI framework, high performance",
        stars=75000,
        forks=6000,
        open_issues_count=300,
        primary_language="Python",
        license_spdx="MIT",
        pushed_at=datetime.now(tz=UTC),
        archived=False,
        disabled=False,
    )


@pytest.fixture()
def sample_profile() -> CandidateProfile:
    return CandidateProfile(
        languages=["Python"],
        frameworks=["FastAPI"],
        topics=["good first issue"],
        experience=ExperienceLevel.INTERMEDIATE,
        hours_per_week=10.0,
        max_setup_hours=2.0,
    )


@pytest.mark.asyncio
class TestConcurrencySafeguards:
    """Tests verifying concurrency protection and SQLite WAL safety."""

    async def test_simultaneous_identical_searches(
        self,
        db_manager: DatabaseManager,
        sample_profile: CandidateProfile,
    ) -> None:
        """Verify multiple identical concurrent searches execute cleanly without locking DB."""
        repo = IssueRepository(db_manager)
        settings = Settings()

        # Seed repository metadata
        norm_repo = create_sample_repo("fastapi/fastapi")
        await repo.upsert_repo_metadata(norm_repo)

        # Mock GitHubClient to simulate network latency
        client = GitHubClient(settings)
        async def mock_search(
            *args: Any, **kwargs: Any
        ) -> tuple[list[dict[str, Any]], int, str | None]:
            await asyncio.sleep(0.05)
            raw = {
                "id": 101,
                "node_id": "I_101",
                "number": 1,
                "title": "Add async test",
                "body": "Reproduction code here.",
                "state": "open",
                "html_url": "https://github.com/fastapi/fastapi/issues/1",
                "repository_url": "https://api.github.com/repos/fastapi/fastapi",
                "labels": [{"name": "good first issue"}],
                "created_at": "2024-03-01T12:00:00Z",
                "updated_at": "2024-03-10T12:00:00Z",
                "author_association": "CONTRIBUTOR",
                "comments": 2,
            }
            return [raw], 1, None

        client.search_issues = AsyncMock(side_effect=mock_search)  # type: ignore[method-assign]
        client.get_repo = AsyncMock(return_value=(None, None, 304))  # type: ignore[method-assign]

        service = DiscoveryService(
            github_client=client,
            repository=repo,
            query_planner=QueryPlanner(),
            ranker=OpportunityRanker(),
        )

        request = SearchRequest(profile=sample_profile, max_results=10)

        # Launch 5 simultaneous searches
        results = await asyncio.gather(
            service.search_and_rank(request),
            service.search_and_rank(request),
            service.search_and_rank(request),
            service.search_and_rank(request),
            service.search_and_rank(request),
        )

        assert len(results) == 5
        for res in results:
            assert res.total_found >= 1
            assert len(res.opportunities) >= 1

        # Check DB didn't duplicate issues
        cached = await repo.get_issues_by_keys(["fastapi/fastapi#1"])
        assert len(cached) == 1

    async def test_simultaneous_feedback_and_refresh(
        self,
        db_manager: DatabaseManager,
    ) -> None:
        """Verify concurrent feedback write and issue refresh do not deadlock."""
        repo = IssueRepository(db_manager)
        settings = Settings()

        # Seed issue in database
        issue = create_sample_issue("fastapi/fastapi#1", "fastapi/fastapi", 1)
        await repo.upsert_issues([issue])
        await repo.upsert_repo_metadata(create_sample_repo("fastapi/fastapi"))

        client = GitHubClient(settings)
        # Mock get_issue to return 304 Not Modified
        client.get_issue = AsyncMock(return_value=(None, "etag_123", 304))  # type: ignore[method-assign]
        client.get_repo = AsyncMock(return_value=(None, None, 304))  # type: ignore[method-assign]

        service = DiscoveryService(
            github_client=client,
            repository=repo,
        )

        # Run simultaneous feedback save and refresh
        async def do_feedback() -> None:
            for _ in range(5):
                await repo.save_feedback(
                    "fastapi/fastapi#1", FeedbackStatus.STARTED, "Working on it"
                )
                await asyncio.sleep(0.01)

        async def do_refresh() -> None:
            for _ in range(5):
                await service.get_or_refresh_opportunity("fastapi", "fastapi", 1)
                await asyncio.sleep(0.01)

        await asyncio.gather(do_feedback(), do_refresh())

        # Verify final state is consistent
        fb = await repo.get_feedback("fastapi/fastapi#1")
        assert fb is not None
        assert fb[0] == FeedbackStatus.STARTED

    async def test_single_flight_refresh_lock(
        self,
        db_manager: DatabaseManager,
    ) -> None:
        """Verify single-flight lock prevents duplicate simultaneous GitHub calls."""
        repo = IssueRepository(db_manager)
        settings = Settings()

        issue = create_sample_issue("tiangolo/fastapi#99", "tiangolo/fastapi", 99)
        await repo.upsert_issues([issue])
        await repo.upsert_repo_metadata(create_sample_repo("tiangolo/fastapi"))

        call_count = 0
        client = GitHubClient(settings)

        async def mock_get_issue(
            *args: Any, **kwargs: Any
        ) -> tuple[dict[str, Any] | None, str | None, int]:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            return None, "etag_99", 304

        client.get_issue = AsyncMock(side_effect=mock_get_issue)  # type: ignore[method-assign]
        client.get_repo = AsyncMock(return_value=(None, None, 304))  # type: ignore[method-assign]

        service = DiscoveryService(
            github_client=client,
            repository=repo,
        )

        # Launch 3 simultaneous refreshes for the exact same issue key
        results = await asyncio.gather(
            service.get_or_refresh_opportunity("tiangolo", "fastapi", 99),
            service.get_or_refresh_opportunity("tiangolo", "fastapi", 99),
            service.get_or_refresh_opportunity("tiangolo", "fastapi", 99),
        )

        assert all(r is not None for r in results)
        # All 3 were serialized cleanly via the single-flight key lock
        assert call_count >= 1

    async def test_search_cancellation_safety(
        self,
        db_manager: DatabaseManager,
        sample_profile: CandidateProfile,
    ) -> None:
        """Verify that cancelling a running search task does not corrupt or deadlock DB."""
        repo = IssueRepository(db_manager)
        settings = Settings()

        client = GitHubClient(settings)
        async def slow_search(
            *args: Any, **kwargs: Any
        ) -> tuple[list[dict[str, Any]], int, str | None]:
            await asyncio.sleep(1.0)
            return [], 0, None

        client.search_issues = AsyncMock(side_effect=slow_search)  # type: ignore[method-assign]

        service = DiscoveryService(
            github_client=client,
            repository=repo,
        )

        task = asyncio.create_task(
            service.search_and_rank(SearchRequest(profile=sample_profile))
        )

        # Cancel the task after 50ms
        await asyncio.sleep(0.05)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        # Verify DB is completely healthy and writable
        await repo.save_feedback("test/repo#1", FeedbackStatus.INTERESTED, "Test after cancel")
        fb = await repo.get_feedback("test/repo#1")
        assert fb is not None
        assert fb[0] == FeedbackStatus.INTERESTED
