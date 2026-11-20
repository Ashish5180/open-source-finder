"""Explainable ranking engine for contribution opportunities.

Adheres strictly to spec Section 6 Stage C:
  - Integrates hard eligibility filters with independent feature scoring.
  - Deterministic tie-breakers: composite_score desc, updated_at desc, issue_key asc.
  - Generates evidence-backed reasons and explicit uncertainty notes.
  - Records versioned scoring config and observation timestamps for reproducibility.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from pydantic import HttpUrl

from app.domain.eligibility import EligibilityEvaluator
from app.domain.scoring import ScoredOpportunity, ScoringEngine
from app.github.normalizer import NormalizedIssue, NormalizedRepo
from app.schemas.models import (
    CandidateProfile,
    Eligibility,
    FeedbackStatus,
    Opportunity,
    SearchResponse,
)

logger = logging.getLogger(__name__)


class OpportunityRanker:
    """Ranks contribution opportunities for a candidate profile."""

    def __init__(
        self,
        scoring_engine: ScoringEngine | None = None,
    ) -> None:
        self.scoring_engine = scoring_engine or ScoringEngine()

    def rank(
        self,
        issues: Sequence[NormalizedIssue],
        profile: CandidateProfile,
        repos_by_key: Mapping[str, NormalizedRepo] | None = None,
        feedback_by_key: Mapping[str, FeedbackStatus] | None = None,
        include_uncertain: bool = True,
        max_results: int = 20,
    ) -> list[Opportunity]:
        """Filter, score, and rank opportunities deterministically."""
        repos = repos_by_key or {}
        feedback_map = feedback_by_key or {}
        now = datetime.now(tz=UTC)

        # 1. Hard Eligibility Filter
        filtered = EligibilityEvaluator.filter_batch(
            issues=issues,
            repos_by_key=dict(repos),
            include_uncertain=include_uncertain,
        )

        scored_list: list[tuple[ScoredOpportunity, Eligibility]] = []

        # 2. Independent Feature Scoring
        for issue, eval_result in filtered:
            repo = repos.get(issue.repository)
            scored = self.scoring_engine.score(
                issue=issue,
                profile=profile,
                repo=repo,
                additional_uncertainties=eval_result.uncertainties,
            )
            scored_list.append((scored, eval_result.eligibility))

        # 3. Deterministic Sorting
        # Key: (-composite_score, -updated_at_epoch, issue_key)
        def sort_key(item: tuple[ScoredOpportunity, Eligibility]) -> tuple[float, float, str]:
            opp = item[0]
            score_val = opp.scores.composite_score
            timestamp_val = opp.issue.updated_at.timestamp()
            key_val = opp.issue.issue_key
            return (-score_val, -timestamp_val, key_val)

        scored_list.sort(key=sort_key)

        # 4. Construct canonical Opportunity models
        opportunities: list[Opportunity] = []
        for scored, eligibility in scored_list[:max_results]:
            issue = scored.issue
            fb = feedback_map.get(issue.issue_key)
            repo = repos.get(issue.repository)

            # Ensure every opportunity has at least one evidence reason
            reasons = list(scored.reasons)
            if not reasons:
                reasons.append("Eligible open issue matching search criteria.")

            opp = Opportunity(
                issue_key=issue.issue_key,
                github_issue_id=issue.github_issue_id,
                url=HttpUrl(issue.url),
                title=issue.title,
                repository=issue.repository,
                labels=list(issue.labels),
                language=repo.primary_language if repo else None,
                state=issue.state,
                is_assigned=issue.is_assigned,
                has_linked_pr=False,  # Linked PR was filtered out or unverified
                created_at=issue.created_at,
                updated_at=issue.updated_at,
                observed_at=now,
                scores=scored.scores,
                eligibility=eligibility,
                exclusion_reason=None,
                reasons=reasons,
                uncertainties=list(scored.uncertainties),
                scoring_config_version=self.scoring_engine.config_version,
                feedback=fb,
            )
            opportunities.append(opp)

        return opportunities

    def build_search_response(
        self,
        ranked_opportunities: list[Opportunity],
        total_found: int,
        total_eligible: int,
        is_cached: bool = False,
        rate_limit_remaining: int | None = None,
        warnings: list[str] | None = None,
    ) -> SearchResponse:
        """Construct the canonical SearchResponse API model."""
        return SearchResponse(
            opportunities=ranked_opportunities,
            total_found=total_found,
            total_eligible=total_eligible,
            scoring_config_version=self.scoring_engine.config_version,
            searched_at=datetime.now(tz=UTC),
            is_cached=is_cached,
            rate_limit_remaining=rate_limit_remaining,
            warnings=warnings or [],
        )
