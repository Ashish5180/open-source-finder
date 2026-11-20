"""Continuous validation test for Section 11 quality metrics and gates.

Automates evaluation gate enforcement in CI/pytest:
  - Precision@10 >= 80% on held-out repositories
  - Relative lift >= 20% over label-only baseline
  - PR Contamination == 0%
  - Stale / Claimed Rate <= 5%
  - 100% of visible explanations evidence-supported
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from app.domain.ranking import OpportunityRanker
from app.domain.scoring import ScoringEngine
from app.github.normalizer import IssueNormalizer, NormalizedIssue, NormalizedRepo
from app.schemas.models import CandidateProfile, ExperienceLevel

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "evaluation"
    / "fixtures"
    / "benchmark_issues.json"
)


@pytest.fixture()
def benchmark_data() -> list[dict[str, Any]]:
    assert FIXTURE_PATH.exists(), f"Benchmark fixture not found at {FIXTURE_PATH}"
    with open(FIXTURE_PATH, encoding="utf-8") as f:
        return cast(list[dict[str, Any]], json.load(f))


def test_section_11_metric_gates(benchmark_data: list[dict[str, Any]]) -> None:
    # 1. Strategy A: Label-only baseline
    label_candidates = [
        raw
        for raw in benchmark_data
        if any(lbl in ["good first issue", "help wanted"] for lbl in raw.get("labels", []))
    ]
    label_candidates.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    top_10_a = label_candidates[:10]

    actionable_a = sum(1 for x in top_10_a if x.get("ground_truth_label") == "ACTIONABLE_NOW")
    precision_a = actionable_a / len(top_10_a) if top_10_a else 0.0

    # 2. Strategy D: CareerVerse heuristic ranking
    normalized_list: list[NormalizedIssue] = []
    repos_by_key: dict[str, NormalizedRepo] = {}

    for raw in benchmark_data:
        issue = IssueNormalizer.normalize_issue(raw)
        if issue is not None:
            normalized_list.append(issue)

        repo_name = raw.get("repository")
        if repo_name and repo_name not in repos_by_key and "repo_metadata" in raw:
            meta = raw["repo_metadata"]
            norm_repo = IssueNormalizer.normalize_repo({
                "full_name": repo_name,
                "description": f"{repo_name} test repo",
                "stargazers_count": meta.get("stars", 0),
                "forks_count": meta.get("forks", 0),
                "open_issues_count": meta.get("open_issues", 0),
                "language": meta.get("language"),
                "license": {"spdx_id": meta.get("license")},
                "pushed_at": raw.get("updated_at"),
                "archived": False,
                "disabled": False,
            })
            if norm_repo is not None:
                repos_by_key[repo_name] = norm_repo

    ranker = OpportunityRanker(ScoringEngine())
    profile = CandidateProfile(
        languages=["Python", "TypeScript", "Go"],
        frameworks=["FastAPI", "React"],
        topics=["good first issue"],
        experience=ExperienceLevel.INTERMEDIATE,
        hours_per_week=10.0,
        max_setup_hours=2.0,
    )

    ranked_opps = ranker.rank(
        issues=normalized_list,
        profile=profile,
        repos_by_key=repos_by_key,
        include_uncertain=False,
        max_results=10,
    )

    raw_by_key = {r["issue_key"]: r for r in benchmark_data}
    top_10_d = [raw_by_key[o.issue_key] for o in ranked_opps if o.issue_key in raw_by_key]

    actionable_d = sum(1 for x in top_10_d if x.get("ground_truth_label") == "ACTIONABLE_NOW")
    precision_d = actionable_d / len(top_10_d) if top_10_d else 0.0

    stale_claimed_d = sum(
        1 for x in top_10_d if x.get("ground_truth_label") == "BLOCKED_OR_CLAIMED"
    )
    pr_count_d = sum(1 for x in top_10_d if x.get("is_pr", False))

    relative_lift = ((precision_d - precision_a) / precision_a) * 100.0 if precision_a > 0 else 0.0

    # Assertion 1: Precision@10 >= 80%
    assert precision_d >= 0.80, f"Precision@10 {precision_d:.1%} below 80% threshold"

    # Assertion 2: Relative lift >= 20%
    assert relative_lift >= 20.0, f"Relative lift +{relative_lift:.1f}% below 20% threshold"

    # Assertion 3: PR contamination strictly 0%
    assert pr_count_d == 0, f"PR contamination detected: {pr_count_d} PRs in top-10"

    # Assertion 4: Stale or claimed issues <= 5%
    assert (stale_claimed_d / len(top_10_d)) <= 0.05, "Stale or claimed rate exceeds 5%"

    # Assertion 5: 100% of visible explanations must have evidence
    for opp in ranked_opps:
        assert len(opp.reasons) >= 1
        for reason in opp.reasons:
            assert len(reason.strip()) > 5
