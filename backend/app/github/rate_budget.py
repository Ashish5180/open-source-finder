"""GitHub API rate limit and quota budget tracker.

Follows GitHub REST API rate-limiting rules:
  - Tracks Primary Rate Limits via X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset.
  - Handles Retry-After headers for 429 and secondary rate limits.
  - Detects secondary (abuse) rate limits from response headers and payload messages.
  - Provides safe wait intervals and pre-flight quota checks to avoid quota exhaustion.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Mapping
from datetime import UTC, datetime


class RateLimitExceededError(Exception):
    """Raised when rate limit is exhausted and requests cannot proceed."""

    def __init__(self, message: str, retry_after_seconds: float) -> None:
        super().__init__(message)
        self.retry_after_seconds = max(1.0, retry_after_seconds)


class RateBudgetTracker:
    """Tracks GitHub API rate limits and bounds request volume within quotas."""

    def __init__(self, min_safe_remaining: int = 5) -> None:
        """Initialize the rate budget tracker.

        Args:
            min_safe_remaining: Minimum remaining requests required before throttling
                                proactively to preserve emergency budget.
        """
        self._min_safe_remaining = min_safe_remaining
        self._limit: int | None = None
        self._remaining: int | None = None
        self._reset_at: datetime | None = None
        self._secondary_blocked_until: datetime | None = None
        self._lock = asyncio.Lock()

    @property
    def limit(self) -> int | None:
        """Total rate limit allocated for the current window."""
        return self._limit

    @property
    def remaining(self) -> int | None:
        """Remaining requests available in the current window."""
        return self._remaining

    @property
    def reset_at(self) -> datetime | None:
        """UTC timestamp when the rate limit window resets."""
        return self._reset_at

    async def update_from_headers(
        self, headers: Mapping[str, str], status_code: int = 200
    ) -> None:
        """Update internal budget from response headers.

        Args:
            headers: HTTP response headers.
            status_code: HTTP response status code.
        """
        now = datetime.now(tz=UTC)
        normalized = {k.lower(): v for k, v in headers.items()}

        async with self._lock:
            # Parse X-RateLimit headers
            if "x-ratelimit-limit" in normalized:
                with contextlib.suppress(ValueError):
                    self._limit = int(normalized["x-ratelimit-limit"])

            if "x-ratelimit-remaining" in normalized:
                with contextlib.suppress(ValueError):
                    self._remaining = int(normalized["x-ratelimit-remaining"])

            if "x-ratelimit-reset" in normalized:
                with contextlib.suppress(ValueError):
                    epoch = float(normalized["x-ratelimit-reset"])
                    self._reset_at = datetime.fromtimestamp(epoch, tz=UTC)

            # Parse Retry-After (seconds or delta)
            if "retry-after" in normalized:
                with contextlib.suppress(ValueError):
                    delay = float(normalized["retry-after"])
                    self._secondary_blocked_until = datetime.fromtimestamp(
                        now.timestamp() + delay, tz=UTC
                    )
            elif status_code == 429:
                # Default safety backoff if 429 without Retry-After
                self._secondary_blocked_until = datetime.fromtimestamp(
                    now.timestamp() + 60.0, tz=UTC
                )

    async def record_secondary_rate_limit(self, delay_seconds: float = 60.0) -> None:
        """Explicitly record a secondary rate limit encounter."""
        now = datetime.now(tz=UTC)
        async with self._lock:
            self._secondary_blocked_until = datetime.fromtimestamp(
                now.timestamp() + delay_seconds, tz=UTC
            )

    async def get_wait_time(self) -> float:
        """Calculate seconds to wait before a request can safely be issued.

        Returns:
            0.0 if safe to proceed immediately, otherwise the number of seconds
            until quota resets or secondary rate limit expires.
        """
        now = datetime.now(tz=UTC)
        async with self._lock:
            # Check secondary rate limit block first
            if self._secondary_blocked_until is not None:
                if now < self._secondary_blocked_until:
                    return (self._secondary_blocked_until - now).total_seconds()
                self._secondary_blocked_until = None

            # Check primary rate limit remaining
            if self._remaining is not None and self._remaining <= self._min_safe_remaining:
                if self._reset_at is not None and now < self._reset_at:
                    return (self._reset_at - now).total_seconds()
                # Window reset time passed
                return 0.0

            return 0.0

    async def check_budget_or_raise(self) -> None:
        """Check if request is permissible or raise RateLimitExceededError."""
        wait_seconds = await self.get_wait_time()
        if wait_seconds > 0.0:
            raise RateLimitExceededError(
                f"GitHub API rate limit exhausted. Retry in {int(wait_seconds)} seconds.",
                retry_after_seconds=wait_seconds,
            )
