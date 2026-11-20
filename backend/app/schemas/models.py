"""Canonical domain models and API contracts.

These Pydantic models form the single source of truth for data flowing
through the application.  GitHub API responses are normalized INTO these
models at the integration boundary, and the frontend receives serialized
versions of these models via the REST API.

Design rules:
  - Never trust a score or status supplied by the client.
  - Never expose the GitHub token in any response.
  - Every score must carry at least one evidence-backed reason.
  - Mark unknown/uncertain data explicitly rather than guessing.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl

# ─── Enumerations ────────────────────────────────────────────────────────────


class Eligibility(StrEnum):
    """Hard eligibility status determined by filters."""

    ELIGIBLE = "ELIGIBLE"
    EXCLUDED = "EXCLUDED"
    UNCERTAIN = "UNCERTAIN"


class ExperienceLevel(StrEnum):
    """Developer experience level for fit scoring."""

    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class FeedbackStatus(StrEnum):
    """Manual feedback a candidate can leave on an opportunity."""

    INTERESTED = "INTERESTED"
    STARTED = "STARTED"
    PR_OPENED = "PR_OPENED"
    MERGED = "MERGED"
    NOT_SUITABLE = "NOT_SUITABLE"
    NOT_ACTIONABLE = "NOT_ACTIONABLE"


class ExclusionReason(StrEnum):
    """Reasons for excluding an issue in hard eligibility filters."""

    CLOSED = "CLOSED"
    NOT_AN_ISSUE = "NOT_AN_ISSUE"
    LOCKED = "LOCKED"
    DUPLICATE = "DUPLICATE"
    WONTFIX = "WONTFIX"
    ASSIGNED = "ASSIGNED"
    HAS_LINKED_PR = "HAS_LINKED_PR"
    STALE_AT_RECHECK = "STALE_AT_RECHECK"
    INACCESSIBLE = "INACCESSIBLE"


# ─── Request Models ──────────────────────────────────────────────────────────


class CandidateProfile(BaseModel):
    """Developer's preferences and constraints for opportunity matching."""

    languages: list[str] = Field(
        ...,
        min_length=1,
        description="Programming languages the candidate knows (e.g. ['Python', 'TypeScript']).",
    )
    frameworks: list[str] = Field(
        default=[],
        description="Frameworks/libraries the candidate is comfortable with.",
    )
    topics: list[str] = Field(
        default=[],
        description="Interest areas (e.g. ['web', 'cli', 'data-science']).",
    )
    experience: ExperienceLevel = Field(
        ...,
        description="Self-assessed experience level.",
    )
    hours_per_week: float = Field(
        ...,
        gt=0,
        le=168,
        description="Hours per week available for contributions.",
    )
    max_setup_hours: float = Field(
        default=2.0,
        ge=0,
        le=40,
        description="Maximum hours willing to spend on project setup.",
    )


class SearchRequest(BaseModel):
    """Request body for the opportunity search endpoint."""

    profile: CandidateProfile
    max_results: int = Field(default=20, ge=1, le=50)
    include_uncertain: bool = Field(
        default=True,
        description="Whether to include UNCERTAIN eligibility issues in results.",
    )


class FeedbackRequest(BaseModel):
    """Request body for submitting feedback on an opportunity."""

    status: FeedbackStatus
    note: str = Field(default="", max_length=500)


class RefreshRequest(BaseModel):
    """Request body for refreshing selected opportunities."""

    issue_keys: list[str] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Issue keys to refresh (e.g. ['owner/repo#123']).",
    )


# ─── Response Models ─────────────────────────────────────────────────────────


class ScoreBreakdown(BaseModel):
    """Detailed breakdown of an opportunity's scores."""

    fit_score: float = Field(..., ge=0.0, le=1.0)
    actionability_score: float = Field(..., ge=0.0, le=1.0)
    health_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="None when repo health data is unavailable.",
    )
    freshness_score: float = Field(..., ge=0.0, le=1.0)
    composite_score: float = Field(..., ge=0.0, le=1.0)


class Opportunity(BaseModel):
    """A ranked open-source contribution opportunity.

    Every opportunity carries evidence-backed reasons and explicit
    uncertainties.  A score is never presented without explanation.
    """

    issue_key: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9._-]+/[a-zA-Z0-9._-]+#\d+$",
        description="Canonical key: 'owner/repo#number'.",
    )
    github_issue_id: int = Field(
        ...,
        description="Stable GitHub issue ID for deduplication.",
    )
    url: HttpUrl
    title: str
    repository: str
    labels: list[str] = Field(default=[])
    language: str | None = Field(
        default=None,
        description="Primary repository language.",
    )
    state: str = Field(
        ...,
        description="Issue state as observed from GitHub (e.g. 'open').",
    )
    is_assigned: bool | None = Field(
        default=None,
        description="None when assignment status is unknown.",
    )
    has_linked_pr: bool | None = Field(
        default=None,
        description="None when linked-PR data is unavailable.",
    )
    created_at: datetime
    updated_at: datetime
    observed_at: datetime = Field(
        ...,
        description="When this snapshot was fetched from GitHub.",
    )
    scores: ScoreBreakdown
    eligibility: Eligibility
    exclusion_reason: ExclusionReason | None = Field(
        default=None,
        description="Set when eligibility is EXCLUDED.",
    )
    reasons: list[str] = Field(
        ...,
        min_length=1,
        description="Evidence-backed explanations for the ranking.",
    )
    uncertainties: list[str] = Field(
        default=[],
        description="Explicit notes about missing or unreliable data.",
    )
    scoring_config_version: str = Field(
        ...,
        description="Which scoring config version produced this result.",
    )
    feedback: FeedbackStatus | None = Field(
        default=None,
        description="Candidate's manual feedback, if any.",
    )


class SearchResponse(BaseModel):
    """Response for the opportunity search endpoint."""

    opportunities: list[Opportunity]
    total_found: int = Field(
        ...,
        ge=0,
        description="Total opportunities found before pagination.",
    )
    total_eligible: int = Field(
        ...,
        ge=0,
        description="Total passing eligibility filters.",
    )
    scoring_config_version: str
    searched_at: datetime
    is_cached: bool = Field(
        default=False,
        description="Whether results came from cache vs fresh fetch.",
    )
    rate_limit_remaining: int | None = Field(
        default=None,
        description="GitHub API rate limit remaining, if known.",
    )
    warnings: list[str] = Field(
        default=[],
        description="Non-fatal warnings (e.g. partial results due to rate limit).",
    )


# ─── Error Contracts ─────────────────────────────────────────────────────────


class ErrorCode(StrEnum):
    """Structured error codes for frontend error handling."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    UPSTREAM_ERROR = "UPSTREAM_ERROR"
    NO_RESULTS = "NO_RESULTS"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorResponse(BaseModel):
    """Structured error response with safe user-facing message."""

    error_code: ErrorCode
    message: str = Field(
        ...,
        description="Safe, user-facing error message.",
    )
    detail: str | None = Field(
        default=None,
        description="Additional context for debugging (never contains secrets).",
    )
    retry_after_seconds: int | None = Field(
        default=None,
        description="Suggested retry delay, if applicable.",
    )


# ─── Health Check ────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    """Response for the /api/health endpoint."""

    status: str = "ok"
    version: str
    database_connected: bool
    github_api_configured: bool = Field(
        ...,
        description="Whether a GitHub token is configured (not its value).",
    )
