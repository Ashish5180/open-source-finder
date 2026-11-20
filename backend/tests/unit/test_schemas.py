"""Comprehensive tests for Pydantic schema validation.

Tests cover:
  - CandidateProfile validation (required fields, bounds, edge cases)
  - SearchRequest validation
  - Opportunity model validation (score ranges, key format, reasons)
  - FeedbackRequest validation
  - RefreshRequest validation
  - ErrorResponse structure
  - HealthResponse structure
  - Enum completeness
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from app.schemas.models import (
    CandidateProfile,
    Eligibility,
    ErrorCode,
    ErrorResponse,
    ExclusionReason,
    ExperienceLevel,
    FeedbackRequest,
    FeedbackStatus,
    HealthResponse,
    Opportunity,
    RefreshRequest,
    ScoreBreakdown,
    SearchRequest,
    SearchResponse,
)

# ─── CandidateProfile ───────────────────────────────────────────────────────


class TestCandidateProfile:
    """Tests for CandidateProfile validation."""

    def test_valid_minimal_profile(self) -> None:
        """Minimal valid profile with only required fields."""
        profile = CandidateProfile(
            languages=["Python"],
            experience=ExperienceLevel.BEGINNER,
            hours_per_week=5.0,
        )
        assert profile.languages == ["Python"]
        assert profile.frameworks == []
        assert profile.topics == []
        assert profile.max_setup_hours == 2.0

    def test_valid_full_profile(self) -> None:
        """Full profile with all optional fields."""
        profile = CandidateProfile(
            languages=["Python", "TypeScript"],
            frameworks=["FastAPI", "React"],
            topics=["web", "cli"],
            experience=ExperienceLevel.ADVANCED,
            hours_per_week=20.0,
            max_setup_hours=4.0,
        )
        assert len(profile.languages) == 2
        assert len(profile.frameworks) == 2

    def test_empty_languages_rejected(self) -> None:
        """Languages list must have at least one entry."""
        with pytest.raises(ValidationError, match="languages"):
            CandidateProfile(
                languages=[],
                experience=ExperienceLevel.BEGINNER,
                hours_per_week=5.0,
            )

    def test_missing_languages_rejected(self) -> None:
        """Languages is required."""
        with pytest.raises(ValidationError):
            CandidateProfile(  # type: ignore[call-arg]
                experience=ExperienceLevel.BEGINNER,
                hours_per_week=5.0,
            )

    def test_zero_hours_rejected(self) -> None:
        """Hours per week must be > 0."""
        with pytest.raises(ValidationError, match="hours_per_week"):
            CandidateProfile(
                languages=["Python"],
                experience=ExperienceLevel.BEGINNER,
                hours_per_week=0,
            )

    def test_negative_hours_rejected(self) -> None:
        """Hours per week must be positive."""
        with pytest.raises(ValidationError):
            CandidateProfile(
                languages=["Python"],
                experience=ExperienceLevel.BEGINNER,
                hours_per_week=-1,
            )

    def test_excessive_hours_rejected(self) -> None:
        """Hours per week must be <= 168."""
        with pytest.raises(ValidationError):
            CandidateProfile(
                languages=["Python"],
                experience=ExperienceLevel.BEGINNER,
                hours_per_week=200,
            )

    def test_negative_setup_hours_rejected(self) -> None:
        """Max setup hours must be >= 0."""
        with pytest.raises(ValidationError):
            CandidateProfile(
                languages=["Python"],
                experience=ExperienceLevel.BEGINNER,
                hours_per_week=5.0,
                max_setup_hours=-1,
            )

    def test_excessive_setup_hours_rejected(self) -> None:
        """Max setup hours must be <= 40."""
        with pytest.raises(ValidationError):
            CandidateProfile(
                languages=["Python"],
                experience=ExperienceLevel.BEGINNER,
                hours_per_week=5.0,
                max_setup_hours=50,
            )

    def test_invalid_experience_rejected(self) -> None:
        """Invalid experience level is rejected."""
        with pytest.raises(ValidationError):
            CandidateProfile(
                languages=["Python"],
                experience="EXPERT",  # type: ignore[arg-type]
                hours_per_week=5.0,
            )

    def test_all_experience_levels_valid(self) -> None:
        """All defined experience levels are accepted."""
        for level in ExperienceLevel:
            profile = CandidateProfile(
                languages=["Python"],
                experience=level,
                hours_per_week=5.0,
            )
            assert profile.experience == level


# ─── SearchRequest ───────────────────────────────────────────────────────────


class TestSearchRequest:
    """Tests for SearchRequest validation."""

    def test_valid_search_request(self) -> None:
        profile = CandidateProfile(
            languages=["Python"],
            experience=ExperienceLevel.INTERMEDIATE,
            hours_per_week=10.0,
        )
        request = SearchRequest(profile=profile)
        assert request.max_results == 20
        assert request.include_uncertain is True

    def test_custom_max_results(self) -> None:
        profile = CandidateProfile(
            languages=["Go"],
            experience=ExperienceLevel.ADVANCED,
            hours_per_week=15.0,
        )
        request = SearchRequest(profile=profile, max_results=5)
        assert request.max_results == 5

    def test_max_results_lower_bound(self) -> None:
        profile = CandidateProfile(
            languages=["Rust"],
            experience=ExperienceLevel.BEGINNER,
            hours_per_week=3.0,
        )
        with pytest.raises(ValidationError, match="max_results"):
            SearchRequest(profile=profile, max_results=0)

    def test_max_results_upper_bound(self) -> None:
        profile = CandidateProfile(
            languages=["Java"],
            experience=ExperienceLevel.INTERMEDIATE,
            hours_per_week=8.0,
        )
        with pytest.raises(ValidationError, match="max_results"):
            SearchRequest(profile=profile, max_results=100)


# ─── ScoreBreakdown ──────────────────────────────────────────────────────────


class TestScoreBreakdown:
    """Tests for score validation."""

    def test_valid_scores(self) -> None:
        scores = ScoreBreakdown(
            fit_score=0.8,
            actionability_score=0.6,
            health_score=0.7,
            freshness_score=0.9,
            composite_score=0.75,
        )
        assert scores.health_score == 0.7

    def test_null_health_score_allowed(self) -> None:
        """Health score can be None when data is unavailable."""
        scores = ScoreBreakdown(
            fit_score=0.5,
            actionability_score=0.5,
            health_score=None,
            freshness_score=0.5,
            composite_score=0.5,
        )
        assert scores.health_score is None

    def test_score_below_zero_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ScoreBreakdown(
                fit_score=-0.1,
                actionability_score=0.5,
                freshness_score=0.5,
                composite_score=0.5,
            )

    def test_score_above_one_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ScoreBreakdown(
                fit_score=1.1,
                actionability_score=0.5,
                freshness_score=0.5,
                composite_score=0.5,
            )


# ─── Opportunity ─────────────────────────────────────────────────────────────


class TestOpportunity:
    """Tests for the Opportunity response model."""

    @pytest.fixture()
    def valid_opportunity_data(self) -> dict[str, Any]:
        """Base valid opportunity data for tests."""
        return {
            "issue_key": "owner/repo#123",
            "github_issue_id": 999999,
            "url": "https://github.com/owner/repo/issues/123",
            "title": "Fix bug in parser",
            "repository": "owner/repo",
            "labels": ["bug", "good first issue"],
            "language": "Python",
            "state": "open",
            "is_assigned": False,
            "has_linked_pr": False,
            "created_at": datetime(2024, 1, 1, tzinfo=UTC),
            "updated_at": datetime(2024, 6, 1, tzinfo=UTC),
            "observed_at": datetime(2024, 6, 15, tzinfo=UTC),
            "scores": {
                "fit_score": 0.85,
                "actionability_score": 0.7,
                "health_score": 0.6,
                "freshness_score": 0.8,
                "composite_score": 0.75,
            },
            "eligibility": Eligibility.ELIGIBLE,
            "reasons": ["Language match: Python", "Recent maintainer activity"],
            "uncertainties": ["Assignment status unverified"],
            "scoring_config_version": "v1.0.0",
        }

    def test_valid_opportunity(self, valid_opportunity_data: dict[str, Any]) -> None:
        opp = Opportunity(**valid_opportunity_data)
        assert opp.issue_key == "owner/repo#123"
        assert opp.eligibility == Eligibility.ELIGIBLE
        assert len(opp.reasons) == 2

    def test_invalid_issue_key_format(self, valid_opportunity_data: dict[str, Any]) -> None:
        """Issue key must match owner/repo#number pattern."""
        valid_opportunity_data["issue_key"] = "invalid-key"
        with pytest.raises(ValidationError, match="issue_key"):
            Opportunity(**valid_opportunity_data)

    def test_empty_reasons_rejected(self, valid_opportunity_data: dict[str, Any]) -> None:
        """Every opportunity must have at least one reason."""
        valid_opportunity_data["reasons"] = []
        with pytest.raises(ValidationError, match="reasons"):
            Opportunity(**valid_opportunity_data)

    def test_unknown_assignment_allowed(self, valid_opportunity_data: dict[str, Any]) -> None:
        """is_assigned can be None to signal uncertainty."""
        valid_opportunity_data["is_assigned"] = None
        opp = Opportunity(**valid_opportunity_data)
        assert opp.is_assigned is None

    def test_unknown_linked_pr_allowed(self, valid_opportunity_data: dict[str, Any]) -> None:
        """has_linked_pr can be None when data is unavailable."""
        valid_opportunity_data["has_linked_pr"] = None
        opp = Opportunity(**valid_opportunity_data)
        assert opp.has_linked_pr is None

    def test_excluded_with_reason(self, valid_opportunity_data: dict[str, Any]) -> None:
        """Excluded opportunities carry an exclusion reason."""
        valid_opportunity_data["eligibility"] = Eligibility.EXCLUDED
        valid_opportunity_data["exclusion_reason"] = ExclusionReason.CLOSED
        opp = Opportunity(**valid_opportunity_data)
        assert opp.exclusion_reason == ExclusionReason.CLOSED


# ─── FeedbackRequest ─────────────────────────────────────────────────────────


class TestFeedbackRequest:
    """Tests for FeedbackRequest validation."""

    def test_valid_feedback(self) -> None:
        fb = FeedbackRequest(status=FeedbackStatus.INTERESTED)
        assert fb.note == ""

    def test_feedback_with_note(self) -> None:
        fb = FeedbackRequest(status=FeedbackStatus.STARTED, note="Looks promising")
        assert fb.note == "Looks promising"

    def test_note_max_length(self) -> None:
        with pytest.raises(ValidationError):
            FeedbackRequest(
                status=FeedbackStatus.NOT_SUITABLE,
                note="x" * 501,
            )

    def test_all_feedback_statuses_valid(self) -> None:
        for status in FeedbackStatus:
            fb = FeedbackRequest(status=status)
            assert fb.status == status


# ─── RefreshRequest ──────────────────────────────────────────────────────────


class TestRefreshRequest:
    """Tests for RefreshRequest validation."""

    def test_valid_refresh(self) -> None:
        req = RefreshRequest(issue_keys=["owner/repo#1"])
        assert len(req.issue_keys) == 1

    def test_empty_keys_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RefreshRequest(issue_keys=[])

    def test_too_many_keys_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RefreshRequest(issue_keys=[f"owner/repo#{i}" for i in range(51)])


# ─── ErrorResponse ───────────────────────────────────────────────────────────


class TestErrorResponse:
    """Tests for ErrorResponse structure."""

    def test_valid_error(self) -> None:
        err = ErrorResponse(
            error_code=ErrorCode.RATE_LIMITED,
            message="GitHub API rate limit exceeded.",
            retry_after_seconds=60,
        )
        assert err.retry_after_seconds == 60

    def test_all_error_codes_exist(self) -> None:
        expected = {
            "VALIDATION_ERROR", "RATE_LIMITED", "UPSTREAM_TIMEOUT",
            "UPSTREAM_ERROR", "NO_RESULTS", "NOT_FOUND", "INTERNAL_ERROR",
        }
        actual = {code.value for code in ErrorCode}
        assert expected == actual


# ─── HealthResponse ──────────────────────────────────────────────────────────


class TestHealthResponse:
    """Tests for HealthResponse structure."""

    def test_healthy(self) -> None:
        h = HealthResponse(
            version="0.1.0",
            database_connected=True,
            github_api_configured=True,
        )
        assert h.status == "ok"

    def test_degraded(self) -> None:
        h = HealthResponse(
            status="degraded",
            version="0.1.0",
            database_connected=False,
            github_api_configured=False,
        )
        assert h.status == "degraded"


# ─── SearchResponse ─────────────────────────────────────────────────────────


class TestSearchResponse:
    """Tests for SearchResponse structure."""

    def test_empty_response(self) -> None:
        resp = SearchResponse(
            opportunities=[],
            total_found=0,
            total_eligible=0,
            scoring_config_version="v1.0.0",
            searched_at=datetime.now(tz=UTC),
        )
        assert resp.total_found == 0
        assert resp.is_cached is False
        assert resp.warnings == []


# ─── Enum Completeness ──────────────────────────────────────────────────────


class TestEnumCompleteness:
    """Verify all enums have the expected members."""

    def test_eligibility_members(self) -> None:
        assert set(Eligibility) == {
            Eligibility.ELIGIBLE,
            Eligibility.EXCLUDED,
            Eligibility.UNCERTAIN,
        }

    def test_experience_level_members(self) -> None:
        assert set(ExperienceLevel) == {
            ExperienceLevel.BEGINNER,
            ExperienceLevel.INTERMEDIATE,
            ExperienceLevel.ADVANCED,
        }

    def test_feedback_status_members(self) -> None:
        expected = {
            "INTERESTED",
            "STARTED",
            "PR_OPENED",
            "MERGED",
            "NOT_SUITABLE",
            "NOT_ACTIONABLE",
        }
        actual = {s.value for s in FeedbackStatus}
        assert expected == actual

    def test_exclusion_reason_members(self) -> None:
        assert len(ExclusionReason) == 9
