"""Hard eligibility filters for GitHub contribution opportunities.

Adheres strictly to spec Section 6 Stage A:
  - Excludes issues that are closed, locked, pull requests, duplicates, wontfix,
    assigned, or in archived/inaccessible repositories.
  - Flags issues with uncertain assignment or linked PR states as UNCERTAIN
    rather than guessing availability.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

from app.github.normalizer import NormalizedIssue, NormalizedRepo
from app.schemas.models import Eligibility, ExclusionReason

WONTFIX_LABELS: tuple[str, ...] = (
    "wontfix",
    "won't fix",
    "wont-fix",
    "invalid",
    "abandoned",
    "rejected",
    "duplicate",
)

DUPLICATE_LABELS: tuple[str, ...] = (
    "duplicate",
    "dup",
)

# Common phrases indicating claimed or duplicate status in text
CLAIMED_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(i am working on this|i'm working on this|working on it)\b", re.IGNORECASE),
    re.compile(r"\b(assigned to me|taking this up|i would like to work on this)\b", re.IGNORECASE),
    re.compile(r"\b(can i take this|pr open|pr submitted)\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class EligibilityResult:
    """The result of applying eligibility filters to an issue."""

    eligibility: Eligibility
    exclusion_reason: ExclusionReason | None = None
    uncertainties: tuple[str, ...] = field(default_factory=tuple)


class EligibilityEvaluator:
    """Evaluates whether a candidate issue is eligible for contribution."""

    @classmethod
    def evaluate(
        cls,
        issue: NormalizedIssue,
        repo: NormalizedRepo | None = None,
        linked_pr_observed: bool | None = None,
    ) -> EligibilityResult:
        """Evaluate hard eligibility filters on an issue.

        Args:
            issue: Normalized issue object.
            repo: Optional repository metadata object.
            linked_pr_observed: Explicit observation of linked pull requests (None if unverified).
        """
        uncertainties: list[str] = []

        # 1. Check if item is actually a Pull Request
        if issue.is_pr:
            return EligibilityResult(
                eligibility=Eligibility.EXCLUDED,
                exclusion_reason=ExclusionReason.NOT_AN_ISSUE,
            )

        # 2. Check state (must be open)
        if issue.state != "open":
            return EligibilityResult(
                eligibility=Eligibility.EXCLUDED,
                exclusion_reason=ExclusionReason.CLOSED,
            )

        # 3. Check locked status
        if issue.locked:
            return EligibilityResult(
                eligibility=Eligibility.EXCLUDED,
                exclusion_reason=ExclusionReason.LOCKED,
            )

        # 4. Check archived/disabled repository
        if repo is not None and (repo.archived or repo.disabled):
            return EligibilityResult(
                eligibility=Eligibility.EXCLUDED,
                exclusion_reason=ExclusionReason.INACCESSIBLE,
            )

        # 5. Check labels for wontfix / invalid / duplicate
        lower_labels = {lbl.lower() for lbl in issue.labels}
        if any(lbl in lower_labels for lbl in DUPLICATE_LABELS):
            return EligibilityResult(
                eligibility=Eligibility.EXCLUDED,
                exclusion_reason=ExclusionReason.DUPLICATE,
            )

        if any(lbl in lower_labels for lbl in WONTFIX_LABELS):
            return EligibilityResult(
                eligibility=Eligibility.EXCLUDED,
                exclusion_reason=ExclusionReason.WONTFIX,
            )

        # 6. Check state reason (e.g. not_planned)
        if issue.state_reason and issue.state_reason in ("not_planned", "completed"):
            return EligibilityResult(
                eligibility=Eligibility.EXCLUDED,
                exclusion_reason=ExclusionReason.WONTFIX,
            )

        # 7. Check assignment status
        if issue.is_assigned is True or issue.assignee_count > 0:
            return EligibilityResult(
                eligibility=Eligibility.EXCLUDED,
                exclusion_reason=ExclusionReason.ASSIGNED,
            )

        # 8. Check linked PRs
        if linked_pr_observed is True:
            return EligibilityResult(
                eligibility=Eligibility.EXCLUDED,
                exclusion_reason=ExclusionReason.HAS_LINKED_PR,
            )

        # 9. Handle Uncertainties (Spec Section 6 Stage A)
        is_uncertain = False

        # If assignment is unknown (None), mark UNCERTAIN
        if issue.is_assigned is None:
            is_uncertain = True
            uncertainties.append("Assignment status could not be fully verified.")

        # Check for potential conversational claiming in body/comments
        if cls._has_claiming_language(issue.body):
            is_uncertain = True
            uncertainties.append("Issue description mentions active contribution work or PR.")

        # If linked PR data has not been verified from timeline, add informative uncertainty
        if linked_pr_observed is None:
            uncertainties.append("Timeline PR verification pending.")

        eligibility_status = (
            Eligibility.UNCERTAIN if is_uncertain else Eligibility.ELIGIBLE
        )

        return EligibilityResult(
            eligibility=eligibility_status,
            exclusion_reason=None,
            uncertainties=tuple(uncertainties),
        )

    @classmethod
    def filter_batch(
        cls,
        issues: Sequence[NormalizedIssue],
        repos_by_key: dict[str, NormalizedRepo] | None = None,
        include_uncertain: bool = True,
    ) -> list[tuple[NormalizedIssue, EligibilityResult]]:
        """Filter a collection of issues, returning eligible and uncertain records."""
        results: list[tuple[NormalizedIssue, EligibilityResult]] = []
        repos = repos_by_key or {}

        for issue in issues:
            repo = repos.get(issue.repository)
            eval_result = cls.evaluate(issue, repo=repo)

            is_eligible = eval_result.eligibility == Eligibility.ELIGIBLE
            is_uncertain_allowed = (
                eval_result.eligibility == Eligibility.UNCERTAIN and include_uncertain
            )
            if is_eligible or is_uncertain_allowed:
                results.append((issue, eval_result))

        return results

    @staticmethod
    def _has_claiming_language(text: str) -> bool:
        if not text:
            return False
        return any(pattern.search(text) for pattern in CLAIMED_PATTERNS)
