"""Unit tests for deterministic opportunity ranking and tie-breaking."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.ranking import OpportunityRanker
from app.github.normalizer import NormalizedIssue, NormalizedRepo
from app.schemas.models import CandidateProfile, ExperienceLevel, FeedbackStatus


@pytest.fixture()
def sample_profile() -> CandidateProfile:
    return CandidateProfile(
        languages=["Python"],
        frameworks=["FastAPI"],
        topics=["api"],
        experience=ExperienceLevel.BEGINNER,
        hours_per_week=10.0,
    )


@pytest.fixture()
def repo_dict() -> dict[str, NormalizedRepo]:
    return {
        "fastapi/fastapi": NormalizedRepo(
            repo_key="fastapi/fastapi",
            description="FastAPI web API",
            stars=70000,
            forks=5000,
            open_issues_count=200,
            primary_language="Python",
            license_spdx="MIT",
            pushed_at=datetime.now(tz=UTC) - timedelta(days=2),
            archived=False,
            disabled=False,
        )
    }


class TestOpportunityRanker:
    """Test suite for deterministic ranking, tie-breaking, and filtering."""

    def test_ranking_is_strictly_deterministic(
        self, sample_profile: CandidateProfile, repo_dict: dict[str, NormalizedRepo]
    ) -> None:
        ranker = OpportunityRanker()
        now = datetime.now(tz=UTC)

        issue_a = NormalizedIssue(
            issue_key="fastapi/fastapi#1",
            github_issue_id=1,
            repository="fastapi/fastapi",
            number=1,
            url="https://github.com/fastapi/fastapi/issues/1",
            title="FastAPI: Add docstring example for route mounting",
            body="Step by step tutorial with ```python\ncode\n``` example.",
            state="open",
            state_reason=None,
            locked=False,
            is_pr=False,
            labels=("good first issue",),
            is_assigned=False,
            assignee_count=0,
            comments_count=1,
            created_at=now,
            updated_at=now,
            closed_at=None,
        )
        issue_b = NormalizedIssue(
            issue_key="fastapi/fastapi#2",
            github_issue_id=2,
            repository="fastapi/fastapi",
            number=2,
            url="https://github.com/fastapi/fastapi/issues/2",
            title="Update typo in README",
            body="Just a typo fix.",
            state="open",
            state_reason=None,
            locked=False,
            is_pr=False,
            labels=(),
            is_assigned=False,
            assignee_count=0,
            comments_count=0,
            created_at=now - timedelta(days=20),
            updated_at=now - timedelta(days=20),
            closed_at=None,
        )

        # Run ranking 5 times: the order of results MUST be identical every single time
        first_run = [
            opp.issue_key
            for opp in ranker.rank([issue_b, issue_a], sample_profile, repo_dict)
        ]

        for _ in range(4):
            subsequent_run = [
                opp.issue_key
                for opp in ranker.rank([issue_a, issue_b], sample_profile, repo_dict)
            ]
            assert first_run == subsequent_run

        # Issue A has higher actionability and good first issue label -> should be rank 1
        assert first_run[0] == "fastapi/fastapi#1"

    def test_deterministic_tie_breaker(
        self, sample_profile: CandidateProfile
    ) -> None:
        ranker = OpportunityRanker()
        base_time = datetime(2024, 6, 1, 12, 0, tzinfo=UTC)

        # Exactly identical issues except keys and updated_at
        issue_newer = NormalizedIssue(
            issue_key="org/repo#10",
            github_issue_id=10,
            repository="org/repo",
            number=10,
            url="https://github.com/org/repo/issues/10",
            title="Identical title",
            body="Identical body with exact character length.",
            state="open",
            state_reason=None,
            locked=False,
            is_pr=False,
            labels=(),
            is_assigned=False,
            assignee_count=0,
            comments_count=0,
            created_at=base_time,
            updated_at=base_time + timedelta(hours=5),
            closed_at=None,
        )
        issue_older = NormalizedIssue(
            issue_key="org/repo#20",
            github_issue_id=20,
            repository="org/repo",
            number=20,
            url="https://github.com/org/repo/issues/20",
            title="Identical title",
            body="Identical body with exact character length.",
            state="open",
            state_reason=None,
            locked=False,
            is_pr=False,
            labels=(),
            is_assigned=False,
            assignee_count=0,
            comments_count=0,
            created_at=base_time,
            updated_at=base_time,
            closed_at=None,
        )

        ranked = ranker.rank([issue_older, issue_newer], sample_profile)
        # Newer update wins tie-break
        assert ranked[0].issue_key == "org/repo#10"

    def test_excludes_unsuitable_issues(
        self, sample_profile: CandidateProfile
    ) -> None:
        ranker = OpportunityRanker()
        dt = datetime.now(tz=UTC)

        closed_issue = NormalizedIssue(
            issue_key="org/repo#30",
            github_issue_id=30,
            repository="org/repo",
            number=30,
            url="https://github.com/org/repo/issues/30",
            title="Closed issue",
            body="",
            state="closed",
            state_reason="completed",
            locked=False,
            is_pr=False,
            labels=(),
            is_assigned=False,
            assignee_count=0,
            comments_count=0,
            created_at=dt,
            updated_at=dt,
            closed_at=dt,
        )
        open_issue = NormalizedIssue(
            issue_key="org/repo#31",
            github_issue_id=31,
            repository="org/repo",
            number=31,
            url="https://github.com/org/repo/issues/31",
            title="Python open task",
            body="Open task.",
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

        ranked = ranker.rank([closed_issue, open_issue], sample_profile)
        assert len(ranked) == 1
        assert ranked[0].issue_key == "org/repo#31"

    def test_attaches_manual_feedback(
        self, sample_profile: CandidateProfile
    ) -> None:
        ranker = OpportunityRanker()
        dt = datetime.now(tz=UTC)

        issue = NormalizedIssue(
            issue_key="org/repo#40",
            github_issue_id=40,
            repository="org/repo",
            number=40,
            url="https://github.com/org/repo/issues/40",
            title="Python task",
            body="Some task.",
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

        feedback_map = {"org/repo#40": FeedbackStatus.STARTED}
        ranked = ranker.rank([issue], sample_profile, feedback_by_key=feedback_map)
        assert ranked[0].feedback == FeedbackStatus.STARTED

    def test_empty_input_returns_empty_list(
        self, sample_profile: CandidateProfile
    ) -> None:
        ranker = OpportunityRanker()
        ranked = ranker.rank([], sample_profile)
        assert ranked == []
