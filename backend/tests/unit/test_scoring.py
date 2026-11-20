"""Unit tests for the independent scoring engine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.scoring import ScoringEngine
from app.github.normalizer import NormalizedIssue, NormalizedRepo
from app.schemas.models import CandidateProfile, ExperienceLevel


@pytest.fixture()
def scoring_engine() -> ScoringEngine:
    return ScoringEngine()


@pytest.fixture()
def beginner_profile() -> CandidateProfile:
    return CandidateProfile(
        languages=["Python"],
        frameworks=["FastAPI"],
        topics=["api"],
        experience=ExperienceLevel.BEGINNER,
        hours_per_week=5.0,
    )


@pytest.fixture()
def active_repo() -> NormalizedRepo:
    return NormalizedRepo(
        repo_key="fastapi/fastapi",
        description="FastAPI framework, high performance, web API",
        stars=75000,
        forks=6000,
        open_issues_count=300,
        primary_language="Python",
        license_spdx="MIT",
        pushed_at=datetime.now(tz=UTC) - timedelta(days=3),
        archived=False,
        disabled=False,
    )


class TestScoringEngine:
    """Test suite for independent scoring dimensions."""

    def test_candidate_fit_language_and_framework(
        self,
        scoring_engine: ScoringEngine,
        beginner_profile: CandidateProfile,
        active_repo: NormalizedRepo,
    ) -> None:
        issue = NormalizedIssue(
            issue_key="fastapi/fastapi#1",
            github_issue_id=1,
            repository="fastapi/fastapi",
            number=1,
            url="https://github.com/fastapi/fastapi/issues/1",
            title="FastAPI tutorial: Add good first issue for custom router",
            body="Good starter task.",
            state="open",
            state_reason=None,
            locked=False,
            is_pr=False,
            labels=("good first issue",),
            is_assigned=False,
            assignee_count=0,
            comments_count=1,
            created_at=datetime.now(tz=UTC),
            updated_at=datetime.now(tz=UTC),
            closed_at=None,
        )

        fit_score, reasons = scoring_engine._score_candidate_fit(
            issue, beginner_profile, active_repo
        )
        assert fit_score >= 0.70
        assert any("Primary repository language match" in r for r in reasons)
        assert any("Framework/topic match" in r for r in reasons)
        assert any("Beginner-friendly" in r for r in reasons)

    def test_actionability_with_code_block_and_acceptance(
        self, scoring_engine: ScoringEngine
    ) -> None:
        body = """
        When parsing request parameters, an invalid integer raises a 500 error instead of 422.

        ### Steps to reproduce
        ```python
        client.get("/items/not-a-number")
        ```

        ### Expected behavior
        - [ ] Should return 422 Unprocessable Entity
        - [ ] Should point to path param in error loc

        See `fastapi/routing.py` for test reference in `tests/test_routing.py`.
        """
        issue = NormalizedIssue(
            issue_key="test/repo#2",
            github_issue_id=2,
            repository="test/repo",
            number=2,
            url="https://github.com/test/repo/issues/2",
            title="Fix parameter validation",
            body=body,
            state="open",
            state_reason=None,
            locked=False,
            is_pr=False,
            labels=(),
            is_assigned=False,
            assignee_count=0,
            comments_count=0,
            created_at=datetime.now(tz=UTC),
            updated_at=datetime.now(tz=UTC),
            closed_at=None,
        )

        act_score, reasons = scoring_engine._score_actionability(issue)
        assert act_score >= 0.80
        assert any("reproduction steps" in r.lower() for r in reasons)
        assert any("acceptance criteria" in r.lower() for r in reasons)
        assert any("test files" in r.lower() for r in reasons)

    def test_repo_health_returns_none_when_repo_missing(
        self, scoring_engine: ScoringEngine
    ) -> None:
        score, reasons = scoring_engine._score_repo_health(None)
        assert score is None
        assert len(reasons) == 0

    def test_repo_health_calculates_with_active_repo(
        self, scoring_engine: ScoringEngine, active_repo: NormalizedRepo
    ) -> None:
        score, reasons = scoring_engine._score_repo_health(active_repo)
        assert score is not None
        assert score >= 0.80
        assert any("Actively maintained" in r for r in reasons)
        assert any("MIT" in r for r in reasons)

    def test_freshness_decay_and_bot_penalty(
        self, scoring_engine: ScoringEngine
    ) -> None:
        # Issue updated 4 days ago
        recent_dt = datetime.now(tz=UTC) - timedelta(days=4)
        issue_recent = NormalizedIssue(
            issue_key="test/repo#3",
            github_issue_id=3,
            repository="test/repo",
            number=3,
            url="https://github.com/test/repo/issues/3",
            title="Clean docstrings",
            body="Need formatting.",
            state="open",
            state_reason=None,
            locked=False,
            is_pr=False,
            labels=(),
            is_assigned=False,
            assignee_count=0,
            comments_count=0,
            created_at=recent_dt,
            updated_at=recent_dt,
            closed_at=None,
            author_association="NONE",
        )
        score_recent, _ = scoring_engine._score_freshness(issue_recent)
        assert score_recent == 1.0

        # Issue updated by a bot
        bot_issue = NormalizedIssue(
            **{**issue_recent.__dict__, "author_association": "BOT"}
        )
        score_bot, _ = scoring_engine._score_freshness(bot_issue)
        assert score_bot < score_recent

    def test_composite_score_renormalization_without_health(
        self, scoring_engine: ScoringEngine, beginner_profile: CandidateProfile
    ) -> None:
        issue = NormalizedIssue(
            issue_key="test/repo#4",
            github_issue_id=4,
            repository="test/repo",
            number=4,
            url="https://github.com/test/repo/issues/4",
            title="Python: Add test",
            body="Short description.",
            state="open",
            state_reason=None,
            locked=False,
            is_pr=False,
            labels=("good first issue",),
            is_assigned=False,
            assignee_count=0,
            comments_count=0,
            created_at=datetime.now(tz=UTC),
            updated_at=datetime.now(tz=UTC),
            closed_at=None,
        )

        scored = scoring_engine.score(issue, beginner_profile, repo=None)
        assert scored.scores.health_score is None
        assert 0.0 <= scored.scores.composite_score <= 1.0
        assert any("Repository health signals unavailable" in u for u in scored.uncertainties)
