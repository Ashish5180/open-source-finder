"""Unit tests for GitHub response normalizer and deduplicator."""

from __future__ import annotations

from datetime import UTC, datetime

from app.github.normalizer import (
    IssueNormalizer,
    NormalizedIssue,
    extract_repo_from_urls,
    parse_iso_datetime,
)


class TestNormalizerUtils:
    """Test utility parsing functions."""

    def test_parse_iso_datetime(self) -> None:
        dt = parse_iso_datetime("2024-03-01T12:00:00Z")
        assert dt is not None
        assert dt == datetime(2024, 3, 1, 12, 0, 0, tzinfo=UTC)

    def test_parse_iso_datetime_invalid(self) -> None:
        assert parse_iso_datetime(None) is None
        assert parse_iso_datetime("") is None
        assert parse_iso_datetime("not-a-date") is None

    def test_extract_repo_from_html_url(self) -> None:
        assert (
            extract_repo_from_urls("https://github.com/facebook/react/issues/123")
            == "facebook/react"
        )
        assert (
            extract_repo_from_urls("https://github.com/fastapi/fastapi/pull/456")
            == "fastapi/fastapi"
        )

    def test_extract_repo_from_repository_url_fallback(self) -> None:
        assert (
            extract_repo_from_urls("", "https://api.github.com/repos/psf/requests")
            == "psf/requests"
        )


class TestIssueNormalizer:
    """Test normalizing raw GitHub search payloads."""

    def test_normalize_valid_issue(self) -> None:
        raw = {
            "id": 101,
            "number": 42,
            "html_url": "https://github.com/pallets/flask/issues/42",
            "title": "Document request context lifecycles",
            "body": "Detailed explanation of application vs request contexts.",
            "state": "open",
            "state_reason": None,
            "locked": False,
            "labels": [
                {"name": "documentation", "color": "0075ca"},
                {"name": "good first issue", "color": "7057ff"},
            ],
            "assignee": None,
            "assignees": [],
            "comments": 3,
            "created_at": "2024-01-10T10:00:00Z",
            "updated_at": "2024-01-15T15:00:00Z",
            "author_association": "MEMBER",
        }

        norm = IssueNormalizer.normalize_issue(raw)
        assert norm is not None
        assert norm.issue_key == "pallets/flask#42"
        assert norm.github_issue_id == 101
        assert norm.repository == "pallets/flask"
        assert norm.is_pr is False
        assert norm.is_assigned is False
        assert "documentation" in norm.labels
        assert "good first issue" in norm.labels
        assert norm.comments_count == 3

    def test_detects_pull_request(self) -> None:
        """Pull requests returned by search API must have is_pr=True."""
        raw = {
            "id": 102,
            "number": 43,
            "html_url": "https://github.com/pallets/flask/pull/43",
            "title": "Fix context leak",
            "state": "open",
            "pull_request": {
                "url": "https://api.github.com/repos/pallets/flask/pulls/43",
                "html_url": "https://github.com/pallets/flask/pull/43",
            },
        }

        norm = IssueNormalizer.normalize_issue(raw)
        assert norm is not None
        assert norm.is_pr is True

    def test_detects_assigned_status(self) -> None:
        raw = {
            "id": 103,
            "number": 44,
            "html_url": "https://github.com/pallets/flask/issues/44",
            "title": "Add test case",
            "state": "open",
            "assignee": {"login": "contributor_one"},
            "assignees": [{"login": "contributor_one"}],
        }

        norm = IssueNormalizer.normalize_issue(raw)
        assert norm is not None
        assert norm.is_assigned is True
        assert norm.assignee_count == 1

    def test_skips_invalid_record(self) -> None:
        assert IssueNormalizer.normalize_issue({}) is None
        assert IssueNormalizer.normalize_issue({"id": 1}) is None
        assert (
            IssueNormalizer.normalize_issue(
                {"id": 1, "number": 10, "html_url": "invalid", "title": "test"}
            )
            is None
        )

    def test_deduplicate_issues(self) -> None:
        dt = datetime(2024, 1, 1, tzinfo=UTC)
        issue1 = NormalizedIssue(
            issue_key="owner/repo#1",
            github_issue_id=1,
            repository="owner/repo",
            number=1,
            url="https://github.com/owner/repo/issues/1",
            title="First",
            body="",
            state="open",
            state_reason=None,
            locked=False,
            is_pr=False,
            labels=("bug",),
            is_assigned=False,
            assignee_count=0,
            comments_count=0,
            created_at=dt,
            updated_at=dt,
            closed_at=None,
        )
        # Duplicate with same id
        issue2 = NormalizedIssue(
            issue_key="owner/repo#1",
            github_issue_id=1,
            repository="owner/repo",
            number=1,
            url="https://github.com/owner/repo/issues/1",
            title="First Duplicate",
            body="",
            state="open",
            state_reason=None,
            locked=False,
            is_pr=False,
            labels=("bug",),
            is_assigned=False,
            assignee_count=0,
            comments_count=0,
            created_at=dt,
            updated_at=dt,
            closed_at=None,
        )
        issue3 = NormalizedIssue(
            issue_key="owner/repo#2",
            github_issue_id=2,
            repository="owner/repo",
            number=2,
            url="https://github.com/owner/repo/issues/2",
            title="Second",
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

        deduped = IssueNormalizer.deduplicate_issues([issue1, issue2, issue3])
        assert len(deduped) == 2
        assert [i.github_issue_id for i in deduped] == [1, 2]
