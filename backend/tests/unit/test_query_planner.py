"""Unit tests for GitHub query planner."""

from __future__ import annotations

from app.github.query_planner import (
    BEGINNER_LABELS,
    QueryPlanner,
    sanitize_search_term,
)
from app.schemas.models import CandidateProfile, ExperienceLevel


class TestQueryPlanner:
    """Test suite for search query generation."""

    def test_sanitize_search_term(self) -> None:
        assert sanitize_search_term('Python: "web"') == "Python web"
        assert sanitize_search_term("(Rust)") == "Rust"
        assert sanitize_search_term("  TypeScript  ") == "TypeScript"

    def test_plan_beginner_queries(self) -> None:
        planner = QueryPlanner(default_per_page=20, default_max_pages=2)
        profile = CandidateProfile(
            languages=["Python"],
            experience=ExperienceLevel.BEGINNER,
            hours_per_week=5.0,
        )

        planned = planner.plan_queries(profile)
        assert len(planned) >= 2
        for q in planned:
            assert "is:issue" in q.q
            assert "is:open" in q.q
            assert 'language:"Python"' in q.q
            assert q.per_page == 20
            assert q.max_pages <= 2

        # Check beginner labels included
        query_strings = [p.q for p in planned]
        assert any(label in q for q in query_strings for label in BEGINNER_LABELS)

    def test_plan_queries_with_frameworks_and_topics(self) -> None:
        planner = QueryPlanner()
        profile = CandidateProfile(
            languages=["TypeScript"],
            frameworks=["React", "Next.js"],
            topics=["frontend"],
            experience=ExperienceLevel.INTERMEDIATE,
            hours_per_week=10.0,
        )

        planned = planner.plan_queries(profile)
        query_strings = [p.q for p in planned]

        assert any('language:"TypeScript"' in q for q in query_strings)
        assert any('"React"' in q for q in query_strings)
        assert any('"frontend"' in q for q in query_strings)

    def test_multiple_languages_planned(self) -> None:
        planner = QueryPlanner()
        profile = CandidateProfile(
            languages=["Go", "Rust"],
            experience=ExperienceLevel.ADVANCED,
            hours_per_week=15.0,
        )

        planned = planner.plan_queries(profile)
        query_strings = [p.q for p in planned]

        assert any('language:"Go"' in q for q in query_strings)
        assert any('language:"Rust"' in q for q in query_strings)

    def test_empty_or_whitespace_language_handled_safely(self) -> None:
        planner = QueryPlanner()
        # Direct call with sanitized terms
        profile = CandidateProfile(
            languages=["Python"],
            frameworks=["   ", '"""'],
            experience=ExperienceLevel.BEGINNER,
            hours_per_week=5.0,
        )
        planned = planner.plan_queries(profile)
        assert len(planned) >= 1
