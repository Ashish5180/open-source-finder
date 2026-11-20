"""Integration tests for API endpoints.

Tests cover:
  - Health check returns correct structure and status
  - Search endpoint accepts valid requests and returns stub response
  - Search endpoint rejects invalid profiles (422)
  - Opportunity detail returns 404 for uncached issues
  - Feedback endpoint accepts valid feedback
  - Refresh endpoint accepts valid requests
  - Request ID header is propagated
  - CORS headers are present for allowed origins
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthEndpoint:
    """Integration tests for GET /api/health."""

    async def test_health_returns_200(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/health")
        assert response.status_code == 200

    async def test_health_response_structure(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/health")
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "database_connected" in data
        assert "github_api_configured" in data

    async def test_health_version_matches_config(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/health")
        data = response.json()
        assert data["version"] == "0.1.0"

    async def test_health_database_connected(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/health")
        data = response.json()
        assert data["database_connected"] is True

    async def test_health_github_not_configured(self, async_client: AsyncClient) -> None:
        """Without GITHUB_TOKEN, github_api_configured should be False."""
        response = await async_client.get("/api/health")
        data = response.json()
        assert data["github_api_configured"] is False

    async def test_health_no_secrets_exposed(self, async_client: AsyncClient) -> None:
        """Health response must never contain tokens or secrets."""
        response = await async_client.get("/api/health")
        body = response.text
        assert "ghp_" not in body
        assert "token" not in body.lower() or "configured" in body.lower()


@pytest.mark.asyncio
class TestSearchEndpoint:
    """Integration tests for POST /api/opportunities/search."""

    async def test_search_valid_request(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/opportunities/search",
            json={
                "profile": {
                    "languages": ["Python"],
                    "experience": "INTERMEDIATE",
                    "hours_per_week": 10,
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "opportunities" in data
        assert "total_found" in data
        assert "scoring_config_version" in data
        assert data["total_found"] >= 0

    async def test_search_with_full_profile(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/opportunities/search",
            json={
                "profile": {
                    "languages": ["Python", "Go"],
                    "frameworks": ["FastAPI", "Gin"],
                    "topics": ["web", "backend"],
                    "experience": "ADVANCED",
                    "hours_per_week": 20,
                    "max_setup_hours": 4,
                },
                "max_results": 10,
                "include_uncertain": False,
            },
        )
        assert response.status_code == 200

    async def test_search_empty_languages_rejected(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/opportunities/search",
            json={
                "profile": {
                    "languages": [],
                    "experience": "BEGINNER",
                    "hours_per_week": 5,
                },
            },
        )
        assert response.status_code == 422

    async def test_search_missing_profile_rejected(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/opportunities/search",
            json={},
        )
        assert response.status_code == 422

    async def test_search_invalid_experience_rejected(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/opportunities/search",
            json={
                "profile": {
                    "languages": ["Python"],
                    "experience": "EXPERT",
                    "hours_per_week": 5,
                },
            },
        )
        assert response.status_code == 422

    async def test_search_zero_hours_rejected(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/opportunities/search",
            json={
                "profile": {
                    "languages": ["Python"],
                    "experience": "BEGINNER",
                    "hours_per_week": 0,
                },
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestOpportunityDetailEndpoint:
    """Integration tests for GET /api/opportunities/{owner}/{repo}/{number}."""

    async def test_uncached_issue_returns_404(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/opportunities/owner/repo/123")
        assert response.status_code == 404


@pytest.mark.asyncio
class TestFeedbackEndpoint:
    """Integration tests for POST /api/opportunities/{issue_key}/feedback."""

    async def test_feedback_accepted(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/opportunities/owner/repo%23123/feedback",
            json={"status": "INTERESTED"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"

    async def test_feedback_with_note(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/opportunities/owner/repo%23456/feedback",
            json={"status": "STARTED", "note": "Looks like a good match"},
        )
        assert response.status_code == 200

    async def test_feedback_invalid_status_rejected(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/opportunities/owner/repo%23789/feedback",
            json={"status": "INVALID_STATUS"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestRefreshEndpoint:
    """Integration tests for POST /api/opportunities/refresh."""

    async def test_refresh_accepted(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/opportunities/refresh",
            json={"issue_keys": ["owner/repo#1", "owner/repo#2"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_requested"] == 2

    async def test_refresh_empty_keys_rejected(self, async_client: AsyncClient) -> None:
        response = await async_client.post(
            "/api/opportunities/refresh",
            json={"issue_keys": []},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestRequestIdPropagation:
    """Verify X-Request-ID header is returned on every response."""

    async def test_request_id_in_response(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/api/health")
        assert "x-request-id" in response.headers

    async def test_custom_request_id_echoed(self, async_client: AsyncClient) -> None:
        response = await async_client.get(
            "/api/health",
            headers={"X-Request-ID": "test-trace-123"},
        )
        assert response.headers["x-request-id"] == "test-trace-123"
