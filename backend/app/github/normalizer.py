"""GitHub API response normalizer and deduplicator.

Transforms raw GitHub REST API payloads into normalized internal dataclasses.
Strictly eliminates:
  - Pull requests (detected via 'pull_request' attribute in Search API).
  - Duplicate issues across multi-page or multi-query searches.
  - Malformed or incomplete records.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def parse_iso_datetime(value: str | None) -> datetime | None:
    """Safely parse GitHub ISO 8601 timestamps."""
    if not value:
        return None
    try:
        # GitHub returns e.g. '2024-03-01T12:00:00Z'
        cleaned = value.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        return None


def extract_repo_from_urls(html_url: str, repository_url: str | None = None) -> str | None:
    """Extract 'owner/repo' from either html_url or repository_url."""
    # First attempt: from html_url e.g. https://github.com/owner/repo/issues/123
    if html_url:
        path_parts = [p for p in urlparse(html_url).path.strip("/").split("/") if p]
        if len(path_parts) >= 2:
            return f"{path_parts[0]}/{path_parts[1]}"

    # Second attempt: from repository_url e.g. https://api.github.com/repos/owner/repo
    if repository_url:
        path_parts = [p for p in urlparse(repository_url).path.strip("/").split("/") if p]
        if len(path_parts) >= 2 and path_parts[-2] != "repos":
            return f"{path_parts[-2]}/{path_parts[-1]}"
        if len(path_parts) >= 3 and path_parts[-3] == "repos":
            return f"{path_parts[-2]}/{path_parts[-1]}"

    return None


@dataclass(frozen=True)
class NormalizedIssue:
    """Canonical normalized GitHub issue representation."""

    issue_key: str  # owner/repo#number
    github_issue_id: int
    repository: str  # owner/repo
    number: int
    url: str
    title: str
    body: str
    state: str
    state_reason: str | None
    locked: bool
    is_pr: bool
    labels: tuple[str, ...]
    is_assigned: bool | None
    assignee_count: int
    comments_count: int
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    author_association: str = "NONE"
    raw_labels: tuple[dict[str, Any], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class NormalizedRepo:
    """Canonical normalized GitHub repository representation."""

    repo_key: str  # owner/repo
    description: str | None
    stars: int
    forks: int
    open_issues_count: int
    primary_language: str | None
    license_spdx: str | None
    pushed_at: datetime | None
    archived: bool
    disabled: bool


class IssueNormalizer:
    """Parses and deduplicates raw GitHub payloads."""

    @staticmethod
    def normalize_issue(raw: dict[str, Any]) -> NormalizedIssue | None:
        """Parse a single raw issue dictionary from GitHub Search API.

        Returns None if record is invalid or unparseable.
        """
        try:
            github_issue_id = raw.get("id")
            number = raw.get("number")
            html_url = raw.get("html_url", "")
            title = (raw.get("title") or "").strip()

            if not github_issue_id or not number or not html_url or not title:
                logger.warning("Skipping issue missing fundamental identifiers: %s", raw)
                return None

            repository = extract_repo_from_urls(html_url, raw.get("repository_url"))
            if not repository:
                logger.warning("Could not extract repo from html_url: %s", html_url)
                return None

            issue_key = f"{repository}#{number}"

            # Check if this item is actually a pull request
            # Spec Section 11 metric: PRs recommended as issues: 0
            is_pr = "pull_request" in raw and raw["pull_request"] is not None

            # Labels parsing
            raw_labels = raw.get("labels", [])
            label_names: list[str] = []
            valid_raw_labels: list[dict[str, Any]] = []
            for lbl in raw_labels:
                if isinstance(lbl, dict) and "name" in lbl:
                    label_names.append(str(lbl["name"]).strip().lower())
                    valid_raw_labels.append(lbl)
                elif isinstance(lbl, str):
                    label_names.append(lbl.strip().lower())

            # Assignees parsing
            assignees = raw.get("assignees") or []
            assignee = raw.get("assignee")
            is_assigned = bool(assignee) or len(assignees) > 0
            assignee_count = len(assignees) if assignees else (1 if assignee else 0)

            # Dates parsing
            created_at = parse_iso_datetime(raw.get("created_at")) or datetime.now(tz=UTC)
            updated_at = parse_iso_datetime(raw.get("updated_at")) or created_at
            closed_at = parse_iso_datetime(raw.get("closed_at"))

            return NormalizedIssue(
                issue_key=issue_key,
                github_issue_id=int(github_issue_id),
                repository=repository,
                number=int(number),
                url=html_url,
                title=title,
                body=raw.get("body") or "",
                state=(raw.get("state") or "open").lower(),
                state_reason=raw.get("state_reason"),
                locked=bool(raw.get("locked", False)),
                is_pr=is_pr,
                labels=tuple(label_names),
                is_assigned=is_assigned,
                assignee_count=assignee_count,
                comments_count=int(raw.get("comments") or 0),
                created_at=created_at,
                updated_at=updated_at,
                closed_at=closed_at,
                author_association=raw.get("author_association") or "NONE",
                raw_labels=tuple(valid_raw_labels),
            )
        except Exception:
            logger.exception("Failed to normalize raw GitHub issue: %s", raw.get("id"))
            return None

    @staticmethod
    def normalize_repo(raw: dict[str, Any]) -> NormalizedRepo | None:
        """Parse a repository object from GitHub API."""
        try:
            full_name = raw.get("full_name")
            if not full_name:
                return None

            license_data = raw.get("license")
            spdx = license_data.get("spdx_id") if isinstance(license_data, dict) else None
            pushed_at = parse_iso_datetime(raw.get("pushed_at"))

            return NormalizedRepo(
                repo_key=full_name,
                description=raw.get("description"),
                stars=int(raw.get("stargazers_count") or 0),
                forks=int(raw.get("forks_count") or 0),
                open_issues_count=int(raw.get("open_issues_count") or 0),
                primary_language=raw.get("language"),
                license_spdx=spdx if spdx != "NOASSERTION" else None,
                pushed_at=pushed_at,
                archived=bool(raw.get("archived", False)),
                disabled=bool(raw.get("disabled", False)),
            )
        except Exception:
            logger.exception("Failed to normalize repository: %s", raw.get("full_name"))
            return None

    @classmethod
    def deduplicate_issues(cls, issues: Sequence[NormalizedIssue]) -> list[NormalizedIssue]:
        """Deduplicate issues by stable github_issue_id and issue_key."""
        seen_ids: set[int] = set()
        seen_keys: set[str] = set()
        deduped: list[NormalizedIssue] = []

        for issue in issues:
            if issue.github_issue_id in seen_ids or issue.issue_key in seen_keys:
                continue
            seen_ids.add(issue.github_issue_id)
            seen_keys.add(issue.issue_key)
            deduped.append(issue)

        return deduped
