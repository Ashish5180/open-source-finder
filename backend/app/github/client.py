"""Resilient GitHub REST API client with bounded concurrency and rate limits.

Adheres strictly to spec Section 8:
  - Managed httpx.AsyncClient lifecycle with bounded connection pool and timeouts.
  - Concurrency bounded by asyncio.Semaphore.
  - Rate budget checking via RateBudgetTracker before issuing requests.
  - Exponential backoff with jitter on transient network/5xx errors.
  - Conditional HTTP requests using ETag / If-None-Match (304 Not Modified).
  - Explicit pagination bounds.
  - Never logs or exposes personal access tokens.
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

import httpx

from app.core.config import Settings
from app.github.rate_budget import RateBudgetTracker, RateLimitExceededError

logger = logging.getLogger(__name__)


class GitHubClientError(Exception):
    """Base exception for GitHub API client errors."""


class GitHubUpstreamTimeoutError(GitHubClientError):
    """Raised when GitHub API request times out."""


class GitHubNotFoundError(GitHubClientError):
    """Raised when a requested resource does not exist (404)."""


class GitHubUpstreamError(GitHubClientError):
    """Raised when GitHub returns a 5xx or unhandled non-2xx status."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"GitHub API error {status_code}: {message}")
        self.status_code = status_code


class GitHubClient:
    """Async client for interacting with the GitHub REST API."""

    def __init__(
        self,
        settings: Settings,
        rate_tracker: RateBudgetTracker | None = None,
        custom_http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self.rate_tracker = rate_tracker or RateBudgetTracker()
        self._semaphore = asyncio.Semaphore(settings.github_max_concurrent_requests)

        self._headers: dict[str, str] = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": f"OpportunityFinder/{settings.app_version}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if settings.github_token is not None:
            token_val = settings.github_token.get_secret_value()
            if token_val.strip():
                self._headers["Authorization"] = f"Bearer {token_val.strip()}"

        self._timeout = httpx.Timeout(
            timeout=settings.github_request_timeout_seconds,
            connect=10.0,
        )

        self._client: httpx.AsyncClient | None = custom_http_client
        self._owns_client = custom_http_client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            limits = httpx.Limits(
                max_connections=self.settings.github_max_concurrent_requests * 2,
                max_keepalive_connections=self.settings.github_max_concurrent_requests,
            )
            self._client = httpx.AsyncClient(
                base_url=self.settings.github_api_base_url,
                headers=self._headers,
                timeout=self._timeout,
                limits=limits,
            )
        return self._client

    async def close(self) -> None:
        """Close underlying HTTP connections."""
        if self._owns_client and self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        etag: str | None = None,
        max_retries: int = 3,
    ) -> tuple[Any, str | None, int]:
        """Execute a rate-budgeted, bounded-concurrency HTTP request.

        Returns:
            Tuple of (parsed_json_or_none, response_etag_or_none, status_code).
        """
        # Pre-flight rate budget check
        await self.rate_tracker.check_budget_or_raise()

        req_headers: dict[str, str] = {}
        if etag:
            req_headers["If-None-Match"] = etag

        client = await self._get_client()

        for attempt in range(max_retries):
            try:
                async with self._semaphore:
                    response = await client.request(
                        method=method,
                        url=path,
                        params=params,
                        headers=req_headers if req_headers else None,
                    )

                # Update rate tracker with response headers
                await self.rate_tracker.update_from_headers(
                    response.headers, status_code=response.status_code
                )
                res_etag = response.headers.get("etag")

                # Handle 304 Not Modified
                if response.status_code == 304:
                    return None, res_etag, 304

                # Handle 404 Not Found
                if response.status_code == 404:
                    raise GitHubNotFoundError(f"Resource at {path} not found")

                # Handle Rate Limiting / Abuse
                if response.status_code in (403, 429):
                    msg = response.text.lower()
                    if "rate limit" in msg or "abuse" in msg or response.status_code == 429:
                        wait_sec = await self.rate_tracker.get_wait_time()
                        raise RateLimitExceededError(
                            "GitHub API rate limit or secondary throttle exceeded",
                            retry_after_seconds=max(wait_sec, 15.0),
                        )
                    # Non-rate-limit 403 (e.g. repo disabled/private)
                    raise GitHubUpstreamError(response.status_code, response.text)

                # Handle 5xx Transient Upstream Errors with exponential backoff
                if response.status_code >= 500:
                    if attempt < max_retries - 1:
                        backoff = (2**attempt) + random.uniform(0.1, 0.5)  # noqa: S311
                        logger.warning(
                            "GitHub 5xx error (%d), retrying in %.2fs",
                            response.status_code,
                            backoff,
                        )
                        await asyncio.sleep(backoff)
                        continue
                    raise GitHubUpstreamError(response.status_code, response.text)

                # Check for other error codes
                if response.status_code >= 400:
                    raise GitHubUpstreamError(response.status_code, response.text)

                return response.json(), res_etag, response.status_code

            except httpx.TimeoutException as exc:
                if attempt < max_retries - 1:
                    backoff = (2**attempt) + random.uniform(0.1, 0.5)  # noqa: S311
                    logger.warning("GitHub request timeout, retrying in %.2fs", backoff)
                    await asyncio.sleep(backoff)
                    continue
                raise GitHubUpstreamTimeoutError(f"Request to {path} timed out") from exc

            except httpx.NetworkError as exc:
                if attempt < max_retries - 1:
                    backoff = (2**attempt) + random.uniform(0.1, 0.5)  # noqa: S311
                    logger.warning("GitHub network error, retrying in %.2fs", backoff)
                    await asyncio.sleep(backoff)
                    continue
                raise GitHubUpstreamError(
                    503, f"Network error connecting to GitHub: {exc}"
                ) from exc

        raise GitHubUpstreamError(500, "Request retries exhausted")

    async def search_issues(
        self,
        query: str,
        sort: str = "updated",
        order: str = "desc",
        per_page: int = 30,
        page: int = 1,
    ) -> tuple[list[dict[str, Any]], int, str | None]:
        """Search issues via /search/issues endpoint.

        Returns:
            Tuple of (items_list, total_count, etag).
        """
        params = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": min(per_page, self.settings.github_results_per_page),
            "page": page,
        }
        data, res_etag, _ = await self.request("GET", "/search/issues", params=params)
        if not isinstance(data, dict):
            return [], 0, res_etag
        items = data.get("items", [])
        total = data.get("total_count", 0)
        return items, total, res_etag

    async def get_issue(
        self,
        owner: str,
        repo: str,
        number: int,
        etag: str | None = None,
    ) -> tuple[dict[str, Any] | None, str | None, int]:
        """Get issue details via /repos/{owner}/{repo}/issues/{number}."""
        path = f"/repos/{owner}/{repo}/issues/{number}"
        data, res_etag, status = await self.request("GET", path, etag=etag)
        return data, res_etag, status

    async def get_repo(
        self,
        owner: str,
        repo: str,
        etag: str | None = None,
    ) -> tuple[dict[str, Any] | None, str | None, int]:
        """Get repository details via /repos/{owner}/{repo}."""
        path = f"/repos/{owner}/{repo}"
        data, res_etag, status = await self.request("GET", path, etag=etag)
        return data, res_etag, status

    async def get_issue_timeline(
        self,
        owner: str,
        repo: str,
        number: int,
        per_page: int = 30,
    ) -> list[dict[str, Any]]:
        """Get issue timeline events for assignment or linked PR discovery."""
        path = f"/repos/{owner}/{repo}/issues/{number}/timeline"
        params = {"per_page": per_page}
        try:
            data, _, _ = await self.request("GET", path, params=params)
            return data if isinstance(data, list) else []
        except GitHubNotFoundError:
            return []
        except Exception as exc:
            logger.warning(
                "Could not fetch timeline for %s/%s#%d: %s",
                owner,
                repo,
                number,
                exc,
            )
            return []
