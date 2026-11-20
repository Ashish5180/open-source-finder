"""Application configuration loaded from environment variables.

Uses pydantic-settings to validate and provide typed access to all config.
The GitHub token is NEVER exposed to the frontend or logged.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────
    app_name: str = "Open-Source Contribution Opportunity Finder"
    app_version: str = "0.1.0"
    debug: bool = False

    # ── GitHub API ───────────────────────────────────────────────────────
    github_token: SecretStr | None = Field(
        default=None,
        description="Personal access token for higher rate limits. Optional for public repos.",
    )
    github_api_base_url: str = "https://api.github.com"
    github_max_concurrent_requests: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Max in-flight GitHub API requests (semaphore bound).",
    )
    github_request_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        description="Per-request timeout for GitHub API calls.",
    )
    github_max_pages_per_query: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Max pages to paginate per search query.",
    )
    github_results_per_page: int = Field(
        default=30,
        ge=1,
        le=100,
        description="Results per page for GitHub search API.",
    )

    # ── Database ─────────────────────────────────────────────────────────
    database_path: Path = Field(
        default=Path("data/opportunities.db"),
        description="Path to SQLite database file.",
    )
    database_busy_timeout_ms: int = Field(
        default=5000,
        ge=100,
        description="SQLite busy_timeout in milliseconds.",
    )

    # ── Server ───────────────────────────────────────────────────────────
    cors_allowed_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins. Restrict to local frontend in dev.",
    )

    # ── Scoring ──────────────────────────────────────────────────────────
    scoring_config_version: str = Field(
        default="v1.0.0",
        description="Versioned identifier for scoring weights/thresholds.",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of application settings."""
    return Settings()
