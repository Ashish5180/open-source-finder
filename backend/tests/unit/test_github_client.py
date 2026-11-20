"""Unit tests for GitHubClient with mock HTTP transport."""

from __future__ import annotations

import httpx
import pytest

from app.core.config import Settings
from app.github.client import (
    GitHubClient,
    GitHubNotFoundError,
    GitHubUpstreamTimeoutError,
)
from app.github.rate_budget import RateBudgetTracker, RateLimitExceededError


@pytest.fixture()
def client_settings() -> Settings:
    return Settings(
        github_max_concurrent_requests=3,
        github_request_timeout_seconds=2.0,
        github_token=None,
    )


@pytest.mark.asyncio
class TestGitHubClient:
    """Test suite for GitHubClient resilience and error handling."""

    async def test_successful_search_issues(self, client_settings: Settings) -> None:
        mock_response = {
            "total_count": 1,
            "items": [
                {
                    "id": 1,
                    "number": 10,
                    "html_url": "https://github.com/org/repo/issues/10",
                    "title": "Good first issue",
                }
            ],
        }

        def handler(request: httpx.Request) -> httpx.Response:
            assert "search/issues" in str(request.url)
            return httpx.Response(
                200,
                json=mock_response,
                headers={"etag": '"etag-123"', "x-ratelimit-remaining": "4900"},
            )

        transport = httpx.MockTransport(handler)
        mock_client = httpx.AsyncClient(transport=transport, base_url="https://api.github.com")

        client = GitHubClient(client_settings, custom_http_client=mock_client)
        items, total, etag = await client.search_issues("is:issue is:open")

        assert total == 1
        assert len(items) == 1
        assert items[0]["id"] == 1
        assert etag == '"etag-123"'
        assert client.rate_tracker.remaining == 4900
        await client.close()

    async def test_etag_304_not_modified(self, client_settings: Settings) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.headers.get("if-none-match") == '"cached-etag"'
            return httpx.Response(304, headers={"etag": '"cached-etag"'})

        transport = httpx.MockTransport(handler)
        mock_client = httpx.AsyncClient(transport=transport, base_url="https://api.github.com")

        client = GitHubClient(client_settings, custom_http_client=mock_client)
        data, etag, status = await client.get_issue("org", "repo", 1, etag='"cached-etag"')

        assert data is None
        assert status == 304
        assert etag == '"cached-etag"'
        await client.close()

    async def test_404_raises_not_found(self, client_settings: Settings) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"message": "Not Found"})

        transport = httpx.MockTransport(handler)
        mock_client = httpx.AsyncClient(transport=transport, base_url="https://api.github.com")

        client = GitHubClient(client_settings, custom_http_client=mock_client)
        with pytest.raises(GitHubNotFoundError):
            await client.get_issue("org", "repo", 999)
        await client.close()

    async def test_403_rate_limit_raises_rate_limit_exceeded(
        self, client_settings: Settings
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                403,
                text="API rate limit exceeded for user",
                headers={"retry-after": "60"},
            )

        transport = httpx.MockTransport(handler)
        mock_client = httpx.AsyncClient(transport=transport, base_url="https://api.github.com")

        client = GitHubClient(client_settings, custom_http_client=mock_client)
        with pytest.raises(RateLimitExceededError) as exc_info:
            await client.search_issues("is:issue")
        assert exc_info.value.retry_after_seconds > 0
        await client.close()

    async def test_preflight_budget_blocks_when_exhausted(
        self, client_settings: Settings
    ) -> None:
        tracker = RateBudgetTracker(min_safe_remaining=5)
        # Manually simulate zero remaining
        await tracker.update_from_headers(
            {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "9999999999"},
            status_code=200,
        )

        transport = httpx.MockTransport(lambda req: httpx.Response(200, json={}))
        mock_client = httpx.AsyncClient(transport=transport, base_url="https://api.github.com")

        client = GitHubClient(
            client_settings, rate_tracker=tracker, custom_http_client=mock_client
        )
        with pytest.raises(RateLimitExceededError):
            await client.search_issues("is:issue")
        await client.close()

    async def test_retry_on_transient_500_then_succeed(
        self, client_settings: Settings
    ) -> None:
        calls = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal calls
            calls += 1
            if calls < 2:
                return httpx.Response(502, text="Bad Gateway")
            return httpx.Response(200, json={"items": [], "total_count": 0})

        transport = httpx.MockTransport(handler)
        mock_client = httpx.AsyncClient(transport=transport, base_url="https://api.github.com")

        client = GitHubClient(client_settings, custom_http_client=mock_client)
        _items, total, _ = await client.search_issues("is:issue")
        assert calls == 2
        assert total == 0
        await client.close()

    async def test_timeout_raises_upstream_timeout(
        self, client_settings: Settings
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Connection timed out")

        transport = httpx.MockTransport(handler)
        mock_client = httpx.AsyncClient(transport=transport, base_url="https://api.github.com")

        client = GitHubClient(client_settings, custom_http_client=mock_client)
        with pytest.raises(GitHubUpstreamTimeoutError):
            await client.search_issues("is:issue")
        await client.close()
