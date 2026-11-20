"""Opportunity API routes.

Thin route handlers that delegate to service layer.
Business logic stays in domain/ and services/ modules.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import cast

from fastapi import APIRouter, HTTPException, Request

from app.schemas.models import (
    ErrorCode,
    ErrorResponse,
    FeedbackRequest,
    Opportunity,
    RefreshRequest,
    SearchRequest,
    SearchResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Search and rank open-source contribution opportunities",
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
        429: {"model": ErrorResponse, "description": "Rate limited"},
        504: {"model": ErrorResponse, "description": "Upstream timeout"},
    },
)
async def search_opportunities(
    body: SearchRequest,
    request: Request,
) -> SearchResponse:
    """Validate preferences, fetch/cache issues, filter and rank.

    This is a stub that will be wired to the discovery service in Phase 2.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(
        "Search request received",
        extra={
            "request_id": request_id,
            "languages": body.profile.languages,
            "experience": body.profile.experience,
        },
    )

    discovery_service = getattr(request.app.state, "discovery_service", None)
    if discovery_service is not None:
        result = await discovery_service.search_and_rank(body)
        return cast(SearchResponse, result)

    return SearchResponse(
        opportunities=[],
        total_found=0,
        total_eligible=0,
        scoring_config_version="v1.0.0",
        searched_at=datetime.now(tz=UTC),
        is_cached=False,
        rate_limit_remaining=None,
        warnings=["Discovery service not initialized."],
    )


@router.get(
    "/{owner}/{repo}/{number}",
    summary="Get cached issue detail and refresh current state",
    response_model=Opportunity,
    responses={
        404: {"model": ErrorResponse, "description": "Issue not found"},
    },
)
async def get_opportunity(
    owner: str,
    repo: str,
    number: int,
    request: Request,
) -> Opportunity:
    """Load cached issue and refresh current state with single-flight recheck."""
    issue_key = f"{owner}/{repo}#{number}"
    logger.info(
        "Issue detail requested",
        extra={
            "request_id": getattr(request.state, "request_id", "unknown"),
            "issue_key": issue_key,
        },
    )

    discovery_service = getattr(request.app.state, "discovery_service", None)
    if discovery_service is not None:
        opportunity = await discovery_service.get_or_refresh_opportunity(owner, repo, number)
        if opportunity is not None:
            return cast(Opportunity, opportunity)

    raise HTTPException(
        status_code=404,
        detail=ErrorResponse(
            error_code=ErrorCode.NOT_FOUND,
            message=f"Issue {issue_key} not found.",
        ).model_dump(),
    )


@router.post(
    "/{issue_key:path}/feedback",
    summary="Save candidate feedback on an opportunity",
    responses={
        404: {"model": ErrorResponse, "description": "Issue not found"},
    },
)
async def submit_feedback(
    issue_key: str,
    body: FeedbackRequest,
    request: Request,
) -> dict[str, str]:
    """Save candidate's manual feedback status."""
    repository = getattr(request.app.state, "repository", None)
    if repository is not None:
        await repository.save_feedback(
            issue_key=issue_key,
            status=body.status,
            note=body.note,
        )

    return {"status": "accepted", "issue_key": issue_key}


@router.post(
    "/refresh",
    summary="Refresh selected or stale opportunities within rate budget",
    responses={
        429: {"model": ErrorResponse, "description": "Rate limited"},
    },
)
async def refresh_opportunities(
    body: RefreshRequest,
    request: Request,
) -> dict[str, object]:
    """Refresh selected/stale results within rate budget."""
    logger.info(
        "Refresh requested",
        extra={
            "request_id": getattr(request.state, "request_id", "unknown"),
            "issue_count": len(body.issue_keys),
        },
    )

    discovery_service = getattr(request.app.state, "discovery_service", None)
    if discovery_service is not None:
        refreshed, total = await discovery_service.refresh_batch(body.issue_keys)
        return {
            "refreshed": refreshed,
            "total_requested": total,
            "message": f"Successfully refreshed {refreshed} of {total} requested issues.",
        }

    return {
        "refreshed": 0,
        "total_requested": len(body.issue_keys),
        "message": "Discovery service not initialized.",
    }
