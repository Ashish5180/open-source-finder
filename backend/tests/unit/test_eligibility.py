"""Unit tests for hard eligibility filters and uncertainty detection."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.eligibility import EligibilityEvaluator
from app.github.normalizer import NormalizedIssue, NormalizedRepo
from app.schemas.models import Eligibility, ExclusionReason


@pytest.fixture()
def base_issue() -> NormalizedIssue:
    dt = datetime(2024, 3, 1, 12, 0, tzinfo=UTC)
    return NormalizedIssue(
        issue_key="fastapi/fastapi#500",
        github_issue_id=7001,
        repository="fastapi/fastapi",
        number=500,
        url="https://github.com/fastapi/fastapi/issues/500",
        title="Add validation for custom UUID format",
        body="We need custom UUID regex validation in path params.",
        state="open",
        state_reason=None,
        locked=False,
        is_pr=False,
        labels=("good first issue", "help wanted"),
        is_assigned=False,
        assignee_count=0,
        comments_count=1,
        created_at=dt,
        updated_at=dt,
        closed_at=None,
    )


class TestEligibilityEvaluator:
    """Test suite for hard eligibility criteria."""

    def test_eligible_open_issue(self, base_issue: NormalizedIssue) -> None:
        result = EligibilityEvaluator.evaluate(base_issue, linked_pr_observed=False)
        assert result.eligibility == Eligibility.ELIGIBLE
        assert result.exclusion_reason is None
        assert len(result.uncertainties) == 0

    def test_pull_requests_excluded_immediately(self, base_issue: NormalizedIssue) -> None:
        pr_issue = NormalizedIssue(
            **{**base_issue.__dict__, "is_pr": True}
        )
        result = EligibilityEvaluator.evaluate(pr_issue)
        assert result.eligibility == Eligibility.EXCLUDED
        assert result.exclusion_reason == ExclusionReason.NOT_AN_ISSUE

    def test_closed_issue_excluded(self, base_issue: NormalizedIssue) -> None:
        closed_issue = NormalizedIssue(
            **{**base_issue.__dict__, "state": "closed"}
        )
        result = EligibilityEvaluator.evaluate(closed_issue)
        assert result.eligibility == Eligibility.EXCLUDED
        assert result.exclusion_reason == ExclusionReason.CLOSED

    def test_locked_issue_excluded(self, base_issue: NormalizedIssue) -> None:
        locked_issue = NormalizedIssue(
            **{**base_issue.__dict__, "locked": True}
        )
        result = EligibilityEvaluator.evaluate(locked_issue)
        assert result.eligibility == Eligibility.EXCLUDED
        assert result.exclusion_reason == ExclusionReason.LOCKED

    def test_wontfix_and_duplicate_labels_excluded(self, base_issue: NormalizedIssue) -> None:
        for label in ("wontfix", "invalid", "duplicate"):
            issue = NormalizedIssue(
                **{**base_issue.__dict__, "labels": (label,)}
            )
            result = EligibilityEvaluator.evaluate(issue)
            assert result.eligibility == Eligibility.EXCLUDED
            assert result.exclusion_reason in (ExclusionReason.WONTFIX, ExclusionReason.DUPLICATE)

    def test_assigned_issue_excluded(self, base_issue: NormalizedIssue) -> None:
        assigned_issue = NormalizedIssue(
            **{**base_issue.__dict__, "is_assigned": True, "assignee_count": 1}
        )
        result = EligibilityEvaluator.evaluate(assigned_issue)
        assert result.eligibility == Eligibility.EXCLUDED
        assert result.exclusion_reason == ExclusionReason.ASSIGNED

    def test_linked_pr_observed_excluded(self, base_issue: NormalizedIssue) -> None:
        result = EligibilityEvaluator.evaluate(base_issue, linked_pr_observed=True)
        assert result.eligibility == Eligibility.EXCLUDED
        assert result.exclusion_reason == ExclusionReason.HAS_LINKED_PR

    def test_archived_repo_excluded(self, base_issue: NormalizedIssue) -> None:
        repo = NormalizedRepo(
            repo_key="fastapi/fastapi",
            description="",
            stars=1000,
            forks=100,
            open_issues_count=5,
            primary_language="Python",
            license_spdx="MIT",
            pushed_at=None,
            archived=True,
            disabled=False,
        )
        result = EligibilityEvaluator.evaluate(base_issue, repo=repo)
        assert result.eligibility == Eligibility.EXCLUDED
        assert result.exclusion_reason == ExclusionReason.INACCESSIBLE

    def test_uncertainty_when_assignment_or_pr_unverified(
        self, base_issue: NormalizedIssue
    ) -> None:
        # None for is_assigned signals unverified assignment state
        unverified_issue = NormalizedIssue(
            **{**base_issue.__dict__, "is_assigned": None}
        )
        result = EligibilityEvaluator.evaluate(unverified_issue, linked_pr_observed=None)
        assert result.eligibility == Eligibility.UNCERTAIN
        assert result.exclusion_reason is None
        assert len(result.uncertainties) >= 1
        assert any("Assignment status" in u for u in result.uncertainties)

    def test_uncertainty_from_claiming_phrases(self, base_issue: NormalizedIssue) -> None:
        claimed_text_issue = NormalizedIssue(
            **{
                **base_issue.__dict__,
                "body": "I am working on this right now, will open PR tomorrow.",
            }
        )
        result = EligibilityEvaluator.evaluate(claimed_text_issue, linked_pr_observed=False)
        assert result.eligibility == Eligibility.UNCERTAIN
        assert any("active contribution work" in u for u in result.uncertainties)

    def test_filter_batch_respects_include_uncertain(self, base_issue: NormalizedIssue) -> None:
        unverified_issue = NormalizedIssue(
            **{**base_issue.__dict__, "issue_key": "fastapi/fastapi#501", "is_assigned": None}
        )
        closed_issue = NormalizedIssue(
            **{**base_issue.__dict__, "issue_key": "fastapi/fastapi#502", "state": "closed"}
        )

        batch = [base_issue, unverified_issue, closed_issue]

        # With include_uncertain=True
        results = EligibilityEvaluator.filter_batch(batch, include_uncertain=True)
        keys = [item[0].issue_key for item in results]
        assert "fastapi/fastapi#500" in keys
        assert "fastapi/fastapi#501" in keys
        assert "fastapi/fastapi#502" not in keys

        # With include_uncertain=False
        strict_results = EligibilityEvaluator.filter_batch(batch, include_uncertain=False)
        strict_keys = [item[0].issue_key for item in strict_results]
        assert "fastapi/fastapi#500" in strict_keys
        assert "fastapi/fastapi#501" not in strict_keys
