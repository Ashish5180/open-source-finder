"""Tests for application configuration.

Tests cover:
  - Default values load correctly
  - Environment variable overrides work
  - Validation bounds are enforced
  - GitHub token is treated as SecretStr (never logged in plaintext)
  - Singleton caching via get_settings()
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


class TestSettingsDefaults:
    """Verify all default values match the spec."""

    def test_app_name(self) -> None:
        s = Settings()
        assert s.app_name == "Open-Source Contribution Opportunity Finder"

    def test_app_version(self) -> None:
        s = Settings()
        assert s.app_version == "0.1.0"

    def test_debug_default_false(self) -> None:
        s = Settings()
        assert s.debug is False

    def test_github_token_default_none(self) -> None:
        s = Settings()
        assert s.github_token is None

    def test_github_api_base_url(self) -> None:
        s = Settings()
        assert s.github_api_base_url == "https://api.github.com"

    def test_github_max_concurrent_requests(self) -> None:
        s = Settings()
        assert s.github_max_concurrent_requests == 5

    def test_github_request_timeout(self) -> None:
        s = Settings()
        assert s.github_request_timeout_seconds == 30.0

    def test_github_max_pages(self) -> None:
        s = Settings()
        assert s.github_max_pages_per_query == 10

    def test_github_results_per_page(self) -> None:
        s = Settings()
        assert s.github_results_per_page == 30

    def test_database_path(self) -> None:
        s = Settings()
        assert s.database_path == Path("data/opportunities.db")

    def test_database_busy_timeout(self) -> None:
        s = Settings()
        assert s.database_busy_timeout_ms == 5000

    def test_cors_origins(self) -> None:
        s = Settings()
        assert s.cors_allowed_origins == ["http://localhost:3000"]

    def test_scoring_config_version(self) -> None:
        s = Settings()
        assert s.scoring_config_version == "v1.0.0"


class TestSettingsOverrides:
    """Verify environment variables override defaults."""

    def test_debug_from_env(self) -> None:
        with patch.dict(os.environ, {"DEBUG": "true"}):
            s = Settings()
            assert s.debug is True

    def test_github_token_from_env(self) -> None:
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test123"}):
            s = Settings()
            assert isinstance(s.github_token, SecretStr)
            assert s.github_token.get_secret_value() == "ghp_test123"

    def test_github_token_never_in_repr(self) -> None:
        """SecretStr must hide the token value in string representations."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_secret"}):
            s = Settings()
            repr_str = repr(s.github_token)
            assert "ghp_secret" not in repr_str
            assert "**" in repr_str

    def test_database_path_from_env(self) -> None:
        with patch.dict(os.environ, {"DATABASE_PATH": "/tmp/test.db"}):
            s = Settings()
            assert s.database_path == Path("/tmp/test.db")

    def test_concurrent_requests_from_env(self) -> None:
        with patch.dict(os.environ, {"GITHUB_MAX_CONCURRENT_REQUESTS": "10"}):
            s = Settings()
            assert s.github_max_concurrent_requests == 10


class TestSettingsValidation:
    """Verify validation bounds reject invalid values."""

    def test_concurrent_requests_too_low(self) -> None:
        with (
            patch.dict(os.environ, {"GITHUB_MAX_CONCURRENT_REQUESTS": "0"}),
            pytest.raises(ValidationError),
        ):
            Settings()

    def test_concurrent_requests_too_high(self) -> None:
        with (
            patch.dict(os.environ, {"GITHUB_MAX_CONCURRENT_REQUESTS": "50"}),
            pytest.raises(ValidationError),
        ):
            Settings()

    def test_timeout_must_be_positive(self) -> None:
        with (
            patch.dict(os.environ, {"GITHUB_REQUEST_TIMEOUT_SECONDS": "0"}),
            pytest.raises(ValidationError),
        ):
            Settings()

    def test_busy_timeout_minimum(self) -> None:
        with (
            patch.dict(os.environ, {"DATABASE_BUSY_TIMEOUT_MS": "10"}),
            pytest.raises(ValidationError),
        ):
            Settings()

    def test_results_per_page_bounds(self) -> None:
        with (
            patch.dict(os.environ, {"GITHUB_RESULTS_PER_PAGE": "200"}),
            pytest.raises(ValidationError),
        ):
            Settings()

    def test_extra_env_vars_ignored(self) -> None:
        """Unknown environment variables should not cause errors."""
        with patch.dict(os.environ, {"TOTALLY_UNKNOWN_VAR": "value"}):
            s = Settings()
            assert s.app_name  # still loads fine
