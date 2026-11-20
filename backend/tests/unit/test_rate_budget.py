"""Unit tests for GitHub RateBudgetTracker."""

from __future__ import annotations

import time

import pytest

from app.github.rate_budget import RateBudgetTracker, RateLimitExceededError


@pytest.mark.asyncio
class TestRateBudgetTracker:
    """Test suite for rate budget tracking logic."""

    async def test_initial_state(self) -> None:
        tracker = RateBudgetTracker()
        assert tracker.limit is None
        assert tracker.remaining is None
        assert tracker.reset_at is None
        assert await tracker.get_wait_time() == 0.0

    async def test_update_from_valid_headers(self) -> None:
        tracker = RateBudgetTracker()
        reset_epoch = time.time() + 3600
        headers = {
            "x-ratelimit-limit": "5000",
            "x-ratelimit-remaining": "4950",
            "x-ratelimit-reset": str(int(reset_epoch)),
        }
        await tracker.update_from_headers(headers, status_code=200)

        assert tracker.limit == 5000
        assert tracker.remaining == 4950
        assert tracker.reset_at is not None
        assert abs(tracker.reset_at.timestamp() - reset_epoch) < 2
        assert await tracker.get_wait_time() == 0.0

    async def test_proactive_throttle_when_remaining_at_min_threshold(self) -> None:
        tracker = RateBudgetTracker(min_safe_remaining=5)
        future_reset = time.time() + 60
        headers = {
            "x-ratelimit-limit": "60",
            "x-ratelimit-remaining": "5",  # <= min_safe_remaining
            "x-ratelimit-reset": str(int(future_reset)),
        }
        await tracker.update_from_headers(headers, status_code=200)

        wait_time = await tracker.get_wait_time()
        assert wait_time > 0.0
        assert wait_time <= 60.0

        with pytest.raises(RateLimitExceededError) as exc_info:
            await tracker.check_budget_or_raise()
        assert exc_info.value.retry_after_seconds > 0

    async def test_retry_after_header_handling(self) -> None:
        tracker = RateBudgetTracker()
        headers = {
            "retry-after": "45",
        }
        await tracker.update_from_headers(headers, status_code=429)

        wait_time = await tracker.get_wait_time()
        assert 40.0 < wait_time <= 45.0

    async def test_status_429_without_retry_after_sets_default_backoff(self) -> None:
        tracker = RateBudgetTracker()
        await tracker.update_from_headers({}, status_code=429)

        wait_time = await tracker.get_wait_time()
        assert 55.0 < wait_time <= 60.0

    async def test_secondary_rate_limit_recording(self) -> None:
        tracker = RateBudgetTracker()
        await tracker.record_secondary_rate_limit(delay_seconds=30.0)

        wait_time = await tracker.get_wait_time()
        assert 25.0 < wait_time <= 30.0

    async def test_malformed_headers_do_not_crash(self) -> None:
        tracker = RateBudgetTracker()
        headers = {
            "x-ratelimit-limit": "not-an-int",
            "x-ratelimit-remaining": "invalid",
            "x-ratelimit-reset": "abc",
            "retry-after": "xyz",
        }
        await tracker.update_from_headers(headers, status_code=200)
        assert tracker.limit is None
        assert tracker.remaining is None
        assert await tracker.get_wait_time() == 0.0
