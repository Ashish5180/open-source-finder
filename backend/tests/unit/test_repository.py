"""Unit tests for SQLite IssueRepository."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio

from app.core.config import Settings
from app.github.normalizer import NormalizedIssue, NormalizedRepo
from app.schemas.models import FeedbackStatus
from app.storage.database import DatabaseManager
from app.storage.repositories import IssueRepository


@pytest.fixture()
def repo_settings(tmp_path: Path) -> Settings:
    return Settings(
        database_path=tmp_path / "repo_test.db",
        database_busy_timeout_ms=1000,
    )


@pytest_asyncio.fixture()
async def repo_db(repo_settings: Settings) -> AsyncGenerator[DatabaseManager, None]:
    manager = DatabaseManager(repo_settings)
    await manager.initialize()
    yield manager
    await manager.close()


@pytest.fixture()
def sample_normalized_issue() -> NormalizedIssue:
    dt = datetime(2024, 2, 1, 10, 0, tzinfo=UTC)
    return NormalizedIssue(
        issue_key="pallets/flask#100",
        github_issue_id=5001,
        repository="pallets/flask",
        number=100,
        url="https://github.com/pallets/flask/issues/100",
        title="Add async route handler support",
        body="Support async def view functions directly.",
        state="open",
        state_reason=None,
        locked=False,
        is_pr=False,
        labels=("feature", "good first issue"),
        is_assigned=False,
        assignee_count=0,
        comments_count=2,
        created_at=dt,
        updated_at=dt,
        closed_at=None,
    )


@pytest.mark.asyncio
class TestIssueRepository:
    """Test suite for repository layer persistence."""

    async def test_upsert_and_retrieve_issue(
        self, repo_db: DatabaseManager, sample_normalized_issue: NormalizedIssue
    ) -> None:
        repo = IssueRepository(repo_db)
        count = await repo.upsert_issues([sample_normalized_issue], etag='"etag1"')
        assert count == 1

        fetched = await repo.get_issue_by_key("pallets/flask#100")
        assert fetched is not None
        assert fetched.issue_key == "pallets/flask#100"
        assert fetched.github_issue_id == 5001
        assert fetched.title == "Add async route handler support"
        assert fetched.labels == ("feature", "good first issue")
        assert fetched.comments_count == 2

    async def test_upsert_is_idempotent(
        self, repo_db: DatabaseManager, sample_normalized_issue: NormalizedIssue
    ) -> None:
        repo = IssueRepository(repo_db)
        await repo.upsert_issues([sample_normalized_issue])

        # Second upsert with updated comments count
        updated_issue = NormalizedIssue(
            issue_key=sample_normalized_issue.issue_key,
            github_issue_id=sample_normalized_issue.github_issue_id,
            repository=sample_normalized_issue.repository,
            number=sample_normalized_issue.number,
            url=sample_normalized_issue.url,
            title="Updated Title",
            body="Updated Body",
            state="open",
            state_reason=None,
            locked=False,
            is_pr=False,
            labels=sample_normalized_issue.labels,
            is_assigned=True,
            assignee_count=1,
            comments_count=5,
            created_at=sample_normalized_issue.created_at,
            updated_at=datetime.now(tz=UTC),
            closed_at=None,
        )
        count = await repo.upsert_issues([updated_issue])
        assert count == 1

        fetched = await repo.get_issue_by_key("pallets/flask#100")
        assert fetched is not None
        assert fetched.title == "Updated Title"
        assert fetched.is_assigned is True
        assert fetched.comments_count == 5

    async def test_get_nonexistent_issue_returns_none(
        self, repo_db: DatabaseManager
    ) -> None:
        repo = IssueRepository(repo_db)
        result = await repo.get_issue_by_key("nonexistent/repo#999")
        assert result is None

    async def test_get_issues_by_keys(
        self, repo_db: DatabaseManager, sample_normalized_issue: NormalizedIssue
    ) -> None:
        repo = IssueRepository(repo_db)
        dt = datetime(2024, 2, 1, 10, 0, tzinfo=UTC)
        issue2 = NormalizedIssue(
            issue_key="pallets/flask#101",
            github_issue_id=5002,
            repository="pallets/flask",
            number=101,
            url="https://github.com/pallets/flask/issues/101",
            title="Second issue",
            body="",
            state="open",
            state_reason=None,
            locked=False,
            is_pr=False,
            labels=(),
            is_assigned=False,
            assignee_count=0,
            comments_count=0,
            created_at=dt,
            updated_at=dt,
            closed_at=None,
        )

        await repo.upsert_issues([sample_normalized_issue, issue2])
        fetched = await repo.get_issues_by_keys(
            ["pallets/flask#100", "pallets/flask#101", "missing#1"]
        )
        assert len(fetched) == 2
        keys = {i.issue_key for i in fetched}
        assert keys == {"pallets/flask#100", "pallets/flask#101"}

    async def test_repo_metadata_persistence(self, repo_db: DatabaseManager) -> None:
        repo = IssueRepository(repo_db)
        meta = NormalizedRepo(
            repo_key="pallets/flask",
            description="The Python micro framework for building web applications.",
            stars=65000,
            forks=16000,
            open_issues_count=12,
            primary_language="Python",
            license_spdx="BSD-3-Clause",
            pushed_at=datetime(2024, 6, 1, tzinfo=UTC),
            archived=False,
            disabled=False,
        )

        await repo.upsert_repo_metadata(meta, etag='"repo-etag"')
        fetched = await repo.get_repo_metadata("pallets/flask")
        assert fetched is not None
        assert fetched.repo_key == "pallets/flask"
        assert fetched.stars == 65000
        assert fetched.primary_language == "Python"
        assert fetched.license_spdx == "BSD-3-Clause"

    async def test_feedback_persistence(self, repo_db: DatabaseManager) -> None:
        repo = IssueRepository(repo_db)
        await repo.save_feedback(
            "pallets/flask#100",
            status=FeedbackStatus.INTERESTED,
            note="Will work on this weekend",
        )

        fb = await repo.get_feedback("pallets/flask#100")
        assert fb is not None
        status, note = fb
        assert status == FeedbackStatus.INTERESTED
        assert note == "Will work on this weekend"

        # Update status
        await repo.save_feedback(
            "pallets/flask#100",
            status=FeedbackStatus.STARTED,
            note="Started drafting PR",
        )
        fb_updated = await repo.get_feedback("pallets/flask#100")
        assert fb_updated is not None
        assert fb_updated[0] == FeedbackStatus.STARTED

        all_fb = await repo.get_all_feedback()
        assert all_fb["pallets/flask#100"] == FeedbackStatus.STARTED
