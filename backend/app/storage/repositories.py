"""Repository layer for SQLite database access.

Adheres strictly to spec Section 8:
  - Atomic, idempotent upserts via sqlite ON CONFLICT DO UPDATE.
  - Short-lived transactions with commit before returning.
  - Never holds database transactions during network calls.
  - Strongly typed domain model conversions.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.github.normalizer import NormalizedIssue, NormalizedRepo
from app.schemas.models import FeedbackStatus
from app.storage.database import DatabaseManager
from app.storage.models import CachedIssueModel, CandidateFeedbackModel, RepoMetadataModel

logger = logging.getLogger(__name__)


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def model_to_normalized_issue(m: CachedIssueModel) -> NormalizedIssue:
    """Convert an ORM model instance to an immutable NormalizedIssue."""
    try:
        labels = tuple(json.loads(m.labels_json))
    except (json.JSONDecodeError, TypeError):
        labels = ()

    created_at = _ensure_utc(m.created_at) or datetime.now(tz=UTC)
    updated_at = _ensure_utc(m.updated_at) or created_at
    closed_at = _ensure_utc(m.closed_at)

    return NormalizedIssue(
        issue_key=m.issue_key,
        github_issue_id=m.github_issue_id,
        repository=m.repository,
        number=m.number,
        url=m.url,
        title=m.title,
        body=m.body,
        state=m.state,
        state_reason=m.state_reason,
        locked=m.locked,
        is_pr=m.is_pr,
        labels=labels,
        is_assigned=m.is_assigned,
        assignee_count=m.assignee_count,
        comments_count=m.comments_count,
        created_at=created_at,
        updated_at=updated_at,
        closed_at=closed_at,
        author_association=m.author_association,
    )


def model_to_normalized_repo(m: RepoMetadataModel) -> NormalizedRepo:
    """Convert an ORM model instance to an immutable NormalizedRepo."""
    return NormalizedRepo(
        repo_key=m.repo_key,
        description=m.description,
        stars=m.stars,
        forks=m.forks,
        open_issues_count=m.open_issues_count,
        primary_language=m.primary_language,
        license_spdx=m.license_spdx,
        pushed_at=_ensure_utc(m.pushed_at),
        archived=m.archived,
        disabled=m.disabled,
    )


class IssueRepository:
    """Repository handling persistence of issues, repos, and feedback."""

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    async def upsert_issues(
        self, issues: Sequence[NormalizedIssue], etag: str | None = None
    ) -> int:
        """Atomically upsert multiple issues into the SQLite database.

        Uses ON CONFLICT(issue_key) DO UPDATE for idempotency.
        """
        if not issues:
            return 0

        now = datetime.now(tz=UTC)
        count = 0

        async with self.db_manager.get_session() as session, session.begin():
            for issue in issues:
                labels_json = json.dumps(list(issue.labels))
                stmt = sqlite_insert(CachedIssueModel).values(
                    issue_key=issue.issue_key,
                    github_issue_id=issue.github_issue_id,
                    repository=issue.repository,
                    number=issue.number,
                    url=issue.url,
                    title=issue.title,
                    body=issue.body,
                    state=issue.state,
                    state_reason=issue.state_reason,
                    locked=issue.locked,
                    is_pr=issue.is_pr,
                    labels_json=labels_json,
                    is_assigned=issue.is_assigned,
                    assignee_count=issue.assignee_count,
                    comments_count=issue.comments_count,
                    created_at=issue.created_at,
                    updated_at=issue.updated_at,
                    closed_at=issue.closed_at,
                    observed_at=now,
                    etag=etag,
                    author_association=issue.author_association,
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=["issue_key"],
                    set_={
                        "title": stmt.excluded.title,
                        "body": stmt.excluded.body,
                        "state": stmt.excluded.state,
                        "state_reason": stmt.excluded.state_reason,
                        "locked": stmt.excluded.locked,
                        "is_pr": stmt.excluded.is_pr,
                        "labels_json": stmt.excluded.labels_json,
                        "is_assigned": stmt.excluded.is_assigned,
                        "assignee_count": stmt.excluded.assignee_count,
                        "comments_count": stmt.excluded.comments_count,
                        "updated_at": stmt.excluded.updated_at,
                        "closed_at": stmt.excluded.closed_at,
                        "observed_at": now,
                        "etag": etag,
                        "author_association": stmt.excluded.author_association,
                    },
                )
                await session.execute(stmt)
                count += 1

        logger.debug("Upserted %d issues into SQLite cache", count)
        return count

    async def get_issue_by_key(self, issue_key: str) -> NormalizedIssue | None:
        """Fetch a single cached issue by canonical key."""
        async with self.db_manager.get_session() as session:
            stmt = select(CachedIssueModel).where(CachedIssueModel.issue_key == issue_key)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return model_to_normalized_issue(model)

    async def get_issue_with_etag(
        self, issue_key: str
    ) -> tuple[NormalizedIssue, str | None] | None:
        """Fetch a single cached issue along with its ETag."""
        async with self.db_manager.get_session() as session:
            stmt = select(CachedIssueModel).where(CachedIssueModel.issue_key == issue_key)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return model_to_normalized_issue(model), model.etag

    async def get_issues_by_keys(self, keys: Sequence[str]) -> list[NormalizedIssue]:
        """Fetch multiple issues by keys in a single query."""
        if not keys:
            return []
        async with self.db_manager.get_session() as session:
            stmt = select(CachedIssueModel).where(CachedIssueModel.issue_key.in_(keys))
            result = await session.execute(stmt)
            models = result.scalars().all()
            return [model_to_normalized_issue(m) for m in models]

    async def upsert_repo_metadata(
        self, repo: NormalizedRepo, etag: str | None = None
    ) -> None:
        """Atomically upsert repository metadata into the cache."""
        now = datetime.now(tz=UTC)
        async with self.db_manager.get_session() as session, session.begin():
            stmt = sqlite_insert(RepoMetadataModel).values(
                repo_key=repo.repo_key,
                description=repo.description,
                stars=repo.stars,
                forks=repo.forks,
                open_issues_count=repo.open_issues_count,
                primary_language=repo.primary_language,
                license_spdx=repo.license_spdx,
                pushed_at=repo.pushed_at,
                archived=repo.archived,
                disabled=repo.disabled,
                observed_at=now,
                etag=etag,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["repo_key"],
                set_={
                    "description": stmt.excluded.description,
                    "stars": stmt.excluded.stars,
                    "forks": stmt.excluded.forks,
                    "open_issues_count": stmt.excluded.open_issues_count,
                    "primary_language": stmt.excluded.primary_language,
                    "license_spdx": stmt.excluded.license_spdx,
                    "pushed_at": stmt.excluded.pushed_at,
                    "archived": stmt.excluded.archived,
                    "disabled": stmt.excluded.disabled,
                    "observed_at": now,
                    "etag": etag,
                },
            )
            await session.execute(stmt)

    async def get_repo_metadata(self, repo_key: str) -> NormalizedRepo | None:
        """Fetch repository metadata by repo key."""
        async with self.db_manager.get_session() as session:
            stmt = select(RepoMetadataModel).where(RepoMetadataModel.repo_key == repo_key)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return model_to_normalized_repo(model)

    async def save_feedback(
        self, issue_key: str, status: FeedbackStatus, note: str = ""
    ) -> None:
        """Save or update candidate feedback for an opportunity."""
        now = datetime.now(tz=UTC)
        async with self.db_manager.get_session() as session, session.begin():
            stmt = sqlite_insert(CandidateFeedbackModel).values(
                issue_key=issue_key,
                status=status.value,
                note=note,
                updated_at=now,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["issue_key"],
                set_={
                    "status": status.value,
                    "note": note,
                    "updated_at": now,
                },
            )
            await session.execute(stmt)

    async def get_feedback(self, issue_key: str) -> tuple[FeedbackStatus, str] | None:
        """Fetch feedback for a given issue."""
        async with self.db_manager.get_session() as session:
            stmt = select(CandidateFeedbackModel).where(
                CandidateFeedbackModel.issue_key == issue_key
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model is None:
                return None
            return FeedbackStatus(model.status), model.note

    async def get_all_feedback(self) -> dict[str, FeedbackStatus]:
        """Fetch all feedback records as an issue_key -> FeedbackStatus map."""
        async with self.db_manager.get_session() as session:
            stmt = select(CandidateFeedbackModel)
            result = await session.execute(stmt)
            models = result.scalars().all()
            return {m.issue_key: FeedbackStatus(m.status) for m in models}
