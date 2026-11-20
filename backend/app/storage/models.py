"""SQLAlchemy 2.0 database models for cached issues and metadata.

Adheres to spec Section 8:
  - Unique constraints on issue_key and github_issue_id prevent duplicate records.
  - Timestamps, etags, and observation times tracked for freshness and 304 recheck.
  - Stored in SQLite with WAL mode.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base class for SQLite tables."""


class CachedIssueModel(Base):
    """Database model for cached GitHub issues."""

    __tablename__ = "cached_issues"

    issue_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    github_issue_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    repository: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    state_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_pr: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    labels_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    is_assigned: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    assignee_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_association: Mapped[str] = mapped_column(String(64), nullable=False, default="NONE")

    __table_args__ = (
        Index("idx_repo_state", "repository", "state"),
        Index("idx_observed_at", "observed_at"),
    )


class RepoMetadataModel(Base):
    """Database model for repository-level metadata and signals."""

    __tablename__ = "repo_metadata"

    repo_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    stars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    forks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    open_issues_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    primary_language: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    license_spdx: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pushed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)


class CandidateFeedbackModel(Base):
    """Database model for candidate manual feedback."""

    __tablename__ = "candidate_feedback"

    issue_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
