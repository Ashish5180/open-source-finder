"""GitHub search query planner.

Translates candidate profile preferences (languages, frameworks, topics, experience)
into structured, bounded GitHub Search API queries adhering to:
  - Spec Section 6: 'is:issue is:open' searches with opportunity labels.
  - Spec Section 8: Bounded pagination caps and deterministic ordering.
  - GitHub REST API search syntax and character constraints.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from app.schemas.models import CandidateProfile, ExperienceLevel

# Labels associated with beginner/starter contributions
BEGINNER_LABELS: tuple[str, ...] = (
    "good first issue",
    "good-first-issue",
    "help wanted",
    "beginner-friendly",
    "easy",
    "starter",
)

# Labels associated with intermediate/general contributions
INTERMEDIATE_LABELS: tuple[str, ...] = (
    "help wanted",
    "help-wanted",
    "contributions welcome",
    "good first issue",
)

# Labels associated with advanced/complex contributions
ADVANCED_LABELS: tuple[str, ...] = (
    "help wanted",
    "contributions welcome",
    "feature",
    "enhancement",
)


@dataclass(frozen=True)
class PlannedQuery:
    """A planned search query for the GitHub Search API."""

    q: str
    sort: str = "updated"
    order: str = "desc"
    per_page: int = 30
    max_pages: int = 2
    priority: int = 1


def sanitize_search_term(term: str) -> str:
    """Sanitize free-text keywords to prevent query syntax injection."""
    cleaned = re.sub(r'[\"\:\(\)]', "", term).strip()
    return cleaned


class QueryPlanner:
    """Plans optimized search queries for a candidate profile."""

    def __init__(
        self,
        default_per_page: int = 30,
        default_max_pages: int = 2,
    ) -> None:
        self.default_per_page = default_per_page
        self.default_max_pages = default_max_pages

    def plan_queries(self, profile: CandidateProfile) -> list[PlannedQuery]:
        """Generate an ordered list of planned queries for the candidate profile.

        Query priority:
          1. Language + Experience-appropriate opportunity labels (Highest signal)
          2. Language + Frameworks / Topics
          3. General opportunity label queries for primary language
        """
        queries: list[PlannedQuery] = []
        labels = self._get_labels_for_experience(profile.experience)

        # Primary queries: Language + top contribution labels
        for lang in profile.languages:
            clean_lang = sanitize_search_term(lang)
            if not clean_lang:
                continue

            # Query 1: Primary opportunity labels (e.g. good first issue / help wanted)
            for label in labels[:2]:
                q = f'is:issue is:open language:"{clean_lang}" label:"{label}"'
                queries.append(
                    PlannedQuery(
                        q=q,
                        sort="updated",
                        order="desc",
                        per_page=self.default_per_page,
                        max_pages=self.default_max_pages,
                        priority=1,
                    )
                )

            # Query 2: Language + Framework or Topic if specified
            terms = [
                sanitize_search_term(t)
                for t in (profile.frameworks + profile.topics)
                if sanitize_search_term(t)
            ]
            for term in terms[:3]:
                q = f'is:issue is:open language:"{clean_lang}" "{term}" label:"help wanted"'
                queries.append(
                    PlannedQuery(
                        q=q,
                        sort="updated",
                        order="desc",
                        per_page=self.default_per_page,
                        max_pages=1,
                        priority=2,
                    )
                )

        # Deduplicate planned queries by query string `q`
        seen_queries: set[str] = set()
        deduped: list[PlannedQuery] = []
        for pq in queries:
            if pq.q not in seen_queries:
                seen_queries.add(pq.q)
                deduped.append(pq)

        return deduped

    def _get_labels_for_experience(self, level: ExperienceLevel) -> Sequence[str]:
        match level:
            case ExperienceLevel.BEGINNER:
                return BEGINNER_LABELS
            case ExperienceLevel.INTERMEDIATE:
                return INTERMEDIATE_LABELS
            case ExperienceLevel.ADVANCED:
                return ADVANCED_LABELS
