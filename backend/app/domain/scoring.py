"""Deterministic, explainable scoring engine for GitHub contribution opportunities.

Adheres strictly to spec Section 6 Stage B:
  - Separate scores for Candidate Fit, Actionability, Repo Health, and Freshness.
  - Scores are normalized in the range [0.0, 1.0].
  - Health score is None when repository data is absent (never invented).
  - Every score produces evidence-backed reasons supported by observed data.
  - Detects bot activity to avoid false freshness inflation.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.github.normalizer import NormalizedIssue, NormalizedRepo
from app.schemas.models import CandidateProfile, ExperienceLevel, ScoreBreakdown

BOT_USERNAMES: tuple[str, ...] = (
    "stale[bot]",
    "github-actions[bot]",
    "dependabot[bot]",
    "snyk-bot",
    "k8s-ci-robot",
)

BEGINNER_KEYWORDS: tuple[str, ...] = (
    "good first issue",
    "good-first-issue",
    "beginner",
    "easy",
    "starter",
    "newcomer",
    "up-for-grabs",
)

INTERMEDIATE_KEYWORDS: tuple[str, ...] = (
    "help wanted",
    "help-wanted",
    "contributions welcome",
    "bug",
)

ADVANCED_KEYWORDS: tuple[str, ...] = (
    "feature",
    "enhancement",
    "architecture",
    "refactor",
    "performance",
)

REPRODUCTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"```[a-zA-Z0-9_-]*\n[\s\S]*?```"),  # code block
    re.compile(r"\b(steps to reproduce|how to reproduce|reproduction|repro)\b", re.IGNORECASE),
    re.compile(r"\b(traceback|stack trace|error log)\b", re.IGNORECASE),
)

ACCEPTANCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(expected behavior|expected result|acceptance criteria)\b", re.IGNORECASE),
    re.compile(r"- \[[ xX]\]"),  # markdown checklist
    re.compile(r"\b(should be|it should|we should)\b", re.IGNORECASE),
)

GUIDANCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(test|tests|unit test|pytest|jest)\b", re.IGNORECASE),
    re.compile(r"\b(in file|located at|see |path:)\b", re.IGNORECASE),
    re.compile(r"[\w/-]+\.(?:py|ts|js|go|rs|java|cpp|c|html|css)\b"),  # file paths
)


@dataclass(frozen=True)
class ScoredOpportunity:
    """An opportunity evaluated with separate score features and evidence."""

    issue: NormalizedIssue
    scores: ScoreBreakdown
    reasons: tuple[str, ...] = field(default_factory=tuple)
    uncertainties: tuple[str, ...] = field(default_factory=tuple)


class ScoringEngine:
    """Deterministic, configurable scoring heuristics."""

    def __init__(
        self,
        weight_fit: float = 0.35,
        weight_actionability: float = 0.30,
        weight_health: float = 0.20,
        weight_freshness: float = 0.15,
        config_version: str = "v1.0.0",
    ) -> None:
        self.w_fit = weight_fit
        self.w_act = weight_actionability
        self.w_health = weight_health
        self.w_fresh = weight_freshness
        self.config_version = config_version

    def score(
        self,
        issue: NormalizedIssue,
        profile: CandidateProfile,
        repo: NormalizedRepo | None = None,
        additional_uncertainties: Sequence[str] = (),
    ) -> ScoredOpportunity:
        """Compute independent scores, composite score, and evidence reasons."""
        reasons: list[str] = []
        uncertainties: list[str] = list(additional_uncertainties)

        # 1. Candidate Fit Score
        fit_score, fit_reasons = self._score_candidate_fit(issue, profile, repo)
        reasons.extend(fit_reasons)

        # 2. Actionability Score
        act_score, act_reasons = self._score_actionability(issue)
        reasons.extend(act_reasons)

        # 3. Repository Health Score (or None)
        health_score, health_reasons = self._score_repo_health(repo)
        if health_reasons:
            reasons.extend(health_reasons)
        else:
            uncertainties.append("Repository health signals unavailable.")

        # 4. Freshness Score
        fresh_score, fresh_reasons = self._score_freshness(issue)
        reasons.extend(fresh_reasons)

        # 5. Composite Score Calculation
        if health_score is not None:
            composite = (
                self.w_fit * fit_score
                + self.w_act * act_score
                + self.w_health * health_score
                + self.w_fresh * fresh_score
            )
        else:
            # Renormalize weights when health is absent
            active_weights = self.w_fit + self.w_act + self.w_fresh
            composite = (
                (self.w_fit * fit_score)
                + (self.w_act * act_score)
                + (self.w_fresh * fresh_score)
            ) / active_weights

        composite = round(max(0.0, min(1.0, composite)), 4)

        scores = ScoreBreakdown(
            fit_score=round(fit_score, 4),
            actionability_score=round(act_score, 4),
            health_score=round(health_score, 4) if health_score is not None else None,
            freshness_score=round(fresh_score, 4),
            composite_score=composite,
        )

        return ScoredOpportunity(
            issue=issue,
            scores=scores,
            reasons=tuple(reasons),
            uncertainties=tuple(uncertainties),
        )

    def _score_candidate_fit(
        self,
        issue: NormalizedIssue,
        profile: CandidateProfile,
        repo: NormalizedRepo | None,
    ) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []
        issue_text = f"{issue.title} {issue.body}".lower()
        issue_labels = [lbl.lower() for lbl in issue.labels]

        # A. Language Match (up to 0.45)
        lang_matched = False
        target_languages = [lang.lower() for lang in profile.languages]
        repo_lang = (repo.primary_language.lower() if repo and repo.primary_language else "")

        for lang in target_languages:
            if repo and repo.primary_language and lang == repo_lang:
                score += 0.45
                reasons.append(f"Primary repository language match: {repo.primary_language}")
                lang_matched = True
                break
            label_match = (
                f'language:"{lang}"' in issue_labels
                or f"language:{lang}" in issue_labels
                or lang in issue_labels
            )
            if label_match:
                score += 0.35
                reasons.append(f"Issue language label match: {lang.title()}")
                lang_matched = True
                break
            if re.search(r"\b" + re.escape(lang) + r"\b", issue_text):
                score += 0.20
                reasons.append(f"Candidate language mentioned in issue: {lang.title()}")
                lang_matched = True
                break

        if not lang_matched:
            score += 0.05  # baseline compatibility

        # B. Framework / Topic Match (up to 0.30)
        target_interests = [f.lower() for f in (profile.frameworks + profile.topics) if f.strip()]
        matched_interests: list[str] = []

        for item in target_interests:
            in_text = item in issue_text or any(item in lbl for lbl in issue_labels)
            in_repo = bool(repo and repo.description and item in repo.description.lower())
            if in_text or in_repo:
                matched_interests.append(item)

        if matched_interests:
            unique_matches = list(dict.fromkeys(matched_interests))[:3]
            score += min(0.30, len(unique_matches) * 0.15)
            reasons.append(f"Framework/topic match: {', '.join(unique_matches)}")

        # C. Experience Level Alignment (up to 0.25)
        match profile.experience:
            case ExperienceLevel.BEGINNER:
                if any(k in issue_labels or k in issue.title.lower() for k in BEGINNER_KEYWORDS):
                    score += 0.25
                    reasons.append("Beginner-friendly opportunity label present")
                elif issue.comments_count <= 2:
                    score += 0.10
                    reasons.append("Low comment contention suitable for first contribution")

            case ExperienceLevel.INTERMEDIATE:
                if any(k in issue_labels for k in INTERMEDIATE_KEYWORDS):
                    score += 0.25
                    reasons.append("Labeled as ready for external contributions ('help wanted')")
                else:
                    score += 0.15

            case ExperienceLevel.ADVANCED:
                if any(k in issue_labels for k in ADVANCED_KEYWORDS):
                    score += 0.25
                    reasons.append("Substantial feature/enhancement matching advanced scope")
                else:
                    score += 0.15

        return min(1.0, score), reasons

    def _score_actionability(self, issue: NormalizedIssue) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []
        body = issue.body or ""

        # A. Description length and structure
        body_len = len(body.strip())
        if body_len >= 300:
            score += 0.25
            reasons.append("Detailed issue description with context")
        elif body_len >= 100:
            score += 0.15
            reasons.append("Clear problem description provided")
        else:
            score += 0.05

        # B. Reproduction code block / error trace
        has_code_block = any(p.search(body) for p in REPRODUCTION_PATTERNS)
        if has_code_block:
            score += 0.30
            reasons.append("Contains reproduction steps, code snippet, or error log")

        # C. Expected behavior / acceptance criteria
        has_acceptance = any(p.search(body) for p in ACCEPTANCE_PATTERNS)
        if has_acceptance:
            score += 0.25
            reasons.append("Clear expected behavior or acceptance criteria outlined")

        # D. Implementation or test guidance
        has_guidance = any(p.search(body) for p in GUIDANCE_PATTERNS)
        if has_guidance:
            score += 0.20
            reasons.append("References test files or specific code paths to modify")

        return min(1.0, score), reasons

    def _score_repo_health(
        self, repo: NormalizedRepo | None
    ) -> tuple[float | None, list[str]]:
        if repo is None:
            return None, []

        score = 0.0
        reasons: list[str] = []
        now = datetime.now(tz=UTC)

        # A. Recent commits / push activity
        if repo.pushed_at is not None:
            pushed_at = (
                repo.pushed_at.replace(tzinfo=UTC)
                if repo.pushed_at.tzinfo is None
                else repo.pushed_at.astimezone(UTC)
            )
            days_since_push = max(0, (now - pushed_at).days)
            if days_since_push <= 14:
                score += 0.40
                reasons.append(f"Actively maintained (pushed {days_since_push} days ago)")
            elif days_since_push <= 45:
                score += 0.30
                reasons.append(f"Regular maintainer activity (pushed {days_since_push} days ago)")
            elif days_since_push <= 90:
                score += 0.15
            else:
                score += 0.05
        else:
            score += 0.10

        # B. Community size / adoption
        if repo.stars >= 500:
            score += 0.25
            reasons.append(f"Established project with community support ({repo.stars:,} stars)")
        elif repo.stars >= 50:
            score += 0.15
            reasons.append(f"Growing open-source project ({repo.stars:,} stars)")
        else:
            score += 0.10

        # C. License
        if repo.license_spdx:
            score += 0.20
            reasons.append(f"Recognized open-source license: {repo.license_spdx}")

        # D. Issue backlog ratio
        if repo.stars > 0:
            ratio = repo.open_issues_count / max(1, repo.stars)
            if ratio < 0.20:
                score += 0.15
                reasons.append("Healthy issue-to-star ratio")

        return min(1.0, score), reasons

    def _score_freshness(self, issue: NormalizedIssue) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []
        now = datetime.now(tz=UTC)

        # Calculate days since last update
        updated_at = (
            issue.updated_at.replace(tzinfo=UTC)
            if issue.updated_at.tzinfo is None
            else issue.updated_at.astimezone(UTC)
        )
        days_since_update = max(0, (now - updated_at).days)

        if days_since_update <= 7:
            score = 1.0
            reasons.append(f"Fresh activity (updated {days_since_update} days ago)")
        elif days_since_update <= 30:
            score = 0.85
            reasons.append(f"Recently updated ({days_since_update} days ago)")
        elif days_since_update <= 90:
            score = 0.60
            reasons.append(f"Updated within last 3 months ({days_since_update} days ago)")
        elif days_since_update <= 180:
            score = 0.35
            reasons.append("Moderate update recency")
        else:
            score = 0.15
            reasons.append(f"Older issue (last updated {days_since_update} days ago)")

        # Bot penalty: reduce freshness if bot triggered recent update
        is_bot_author = issue.author_association == "BOT"
        has_bot_title = any(bot in issue.title.lower() for bot in BOT_USERNAMES)
        if is_bot_author or has_bot_title:
            score = max(0.1, score - 0.35)

        return score, reasons
