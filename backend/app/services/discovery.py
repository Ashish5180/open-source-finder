"""Discovery and orchestration service for contribution opportunities.

Adheres strictly to spec Section 2, 6, and 8:
  - Coordinates query planning, GitHub fetching, cache upserts, and ranking.
  - Spec rule: Never holds a SQLite transaction open during network I/O.
  - Bounded concurrency and rate-limit aware.
  - Formats responses with explanations and uncertainty notes.
"""

import asyncio
import logging
from collections.abc import Sequence
from typing import Any

from app.domain.ranking import OpportunityRanker
from app.github.client import GitHubClient
from app.github.normalizer import IssueNormalizer, NormalizedIssue, NormalizedRepo
from app.github.query_planner import QueryPlanner
from app.github.rate_budget import RateLimitExceededError
from app.schemas.models import (
    CandidateProfile,
    ExperienceLevel,
    Opportunity,
    SearchRequest,
    SearchResponse,
)
from app.storage.repositories import IssueRepository

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Service orchestrating opportunity discovery, caching, and ranking."""

    def __init__(
        self,
        github_client: GitHubClient,
        repository: IssueRepository,
        query_planner: QueryPlanner | None = None,
        ranker: OpportunityRanker | None = None,
    ) -> None:
        self.github_client = github_client
        self.repository = repository
        self.query_planner = query_planner or QueryPlanner()
        self.ranker = ranker or OpportunityRanker()
        self._in_flight_locks: dict[str, asyncio.Lock] = {}
        self._registry_lock = asyncio.Lock()

    async def _get_key_lock(self, key: str) -> asyncio.Lock:
        async with self._registry_lock:
            if key not in self._in_flight_locks:
                self._in_flight_locks[key] = asyncio.Lock()
            return self._in_flight_locks[key]

    async def search_and_rank(self, request: SearchRequest) -> SearchResponse:
        """Execute planned queries, normalize, cache, score, and rank opportunities."""
        profile = request.profile
        warnings: list[str] = []
        all_raw_issues: list[dict[str, Any]] = []

        # 1. Plan Queries based on candidate profile
        planned_queries = self.query_planner.plan_queries(profile)

        # 2. Fetch Issues from GitHub Search API (without holding any DB transactions)
        for planned in planned_queries:
            try:
                for page in range(1, planned.max_pages + 1):
                    items, _total, _ = await self.github_client.search_issues(
                        query=planned.q,
                        sort=planned.sort,
                        order=planned.order,
                        per_page=planned.per_page,
                        page=page,
                    )
                    all_raw_issues.extend(items)
                    reached_cap = len(all_raw_issues) >= request.max_results * 4
                    if len(items) < planned.per_page or reached_cap:
                        break
            except RateLimitExceededError as exc:
                logger.warning("Search rate limit encountered: %s", exc)
                warnings.append(f"Search partially throttled by rate limit: {exc}")
                break
            except Exception as exc:
                logger.warning("Error executing search query '%s': %s", planned.q, exc)
                warnings.append(f"Partial search failure: {exc}")

        # 3. Normalize and Deduplicate Issues
        normalized: list[NormalizedIssue] = []
        for raw in all_raw_issues:
            issue = IssueNormalizer.normalize_issue(raw)
            if issue is not None:
                normalized.append(issue)

        deduped_issues = IssueNormalizer.deduplicate_issues(normalized)

        # 4. Short SQLite write transaction to update snapshot cache
        if deduped_issues:
            await self.repository.upsert_issues(deduped_issues)

        # 5. Fetch Repository Metadata for top unique repositories
        unique_repos = list({i.repository for i in deduped_issues})[:10]
        repos_by_key: dict[str, NormalizedRepo] = {}

        for repo_name in unique_repos:
            parts = repo_name.split("/")
            if len(parts) == 2:
                owner, repo = parts
                # Check DB cache first
                cached_repo = await self.repository.get_repo_metadata(repo_name)
                if cached_repo is not None:
                    repos_by_key[repo_name] = cached_repo
                else:
                    # Fetch from GitHub API without holding DB lock
                    try:
                        repo_data, etag, _status = await self.github_client.get_repo(owner, repo)
                        if repo_data is not None:
                            norm_repo = IssueNormalizer.normalize_repo(repo_data)
                            if norm_repo is not None:
                                repos_by_key[repo_name] = norm_repo
                                await self.repository.upsert_repo_metadata(norm_repo, etag=etag)
                    except Exception as exc:
                        logger.debug("Could not fetch metadata for repo %s: %s", repo_name, exc)

        # 6. Fetch Existing Candidate Feedback
        feedback_map = await self.repository.get_all_feedback()

        # 7. Filter, Score, and Rank Opportunities
        ranked = self.ranker.rank(
            issues=deduped_issues,
            profile=profile,
            repos_by_key=repos_by_key,
            feedback_by_key=feedback_map,
            include_uncertain=request.include_uncertain,
            max_results=request.max_results,
        )

        return self.ranker.build_search_response(
            ranked_opportunities=ranked,
            total_found=len(deduped_issues),
            total_eligible=len(ranked),
            is_cached=False,
            rate_limit_remaining=self.github_client.rate_tracker.remaining,
            warnings=warnings,
        )

    async def get_or_refresh_opportunity(
        self,
        owner: str,
        repo: str,
        number: int,
        profile: CandidateProfile | None = None,
    ) -> Opportunity | None:
        """Fetch cached issue or recheck live with single-flight concurrency lock."""
        issue_key = f"{owner}/{repo}#{number}"
        key_lock = await self._get_key_lock(issue_key)

        async with key_lock:
            # Check local DB snapshot first
            cached_entry = await self.repository.get_issue_with_etag(issue_key)
            stored_issue = cached_entry[0] if cached_entry else None
            stored_etag = cached_entry[1] if cached_entry else None

            # Recheck with GitHub API outside DB transaction
            norm_issue = stored_issue
            try:
                data, res_etag, status = await self.github_client.get_issue(
                    owner, repo, number, etag=stored_etag
                )
                if status == 200 and data is not None:
                    parsed = IssueNormalizer.normalize_issue(data)
                    if parsed is not None:
                        norm_issue = parsed
                        await self.repository.upsert_issues([parsed], etag=res_etag)
                elif status == 304 and stored_issue is not None:
                    norm_issue = stored_issue
                elif status == 404:
                    return None
            except Exception as exc:
                logger.debug("Failed upstream recheck for %s: %s", issue_key, exc)
                # Fallback to stored snapshot if available
                if stored_issue is None:
                    return None
                norm_issue = stored_issue

            if norm_issue is None:
                return None

            # Fetch repo metadata
            repo_key = f"{owner}/{repo}"
            repo_meta = await self.repository.get_repo_metadata(repo_key)
            if repo_meta is None:
                try:
                    repo_data, repo_etag, _status = await self.github_client.get_repo(owner, repo)
                    if repo_data is not None:
                        parsed_repo = IssueNormalizer.normalize_repo(repo_data)
                        if parsed_repo is not None:
                            await self.repository.upsert_repo_metadata(
                                parsed_repo, etag=repo_etag
                            )
                            repo_meta = parsed_repo
                except Exception as exc:
                    logger.debug("Failed upstream repo fetch for %s: %s", repo_key, exc)

            # Fetch feedback
            fb_entry = await self.repository.get_feedback(issue_key)
            fb_status = fb_entry[0] if fb_entry else None

            # Calibrate profile for scoring if none provided
            candidate_profile = profile or CandidateProfile(
                languages=(
                    [repo_meta.primary_language]
                    if repo_meta and repo_meta.primary_language
                    else ["Python"]
                ),
                experience=ExperienceLevel.INTERMEDIATE,
                hours_per_week=10.0,
                max_setup_hours=2.0,
            )

            ranked = self.ranker.rank(
                issues=[norm_issue],
                profile=candidate_profile,
                repos_by_key={norm_issue.repository: repo_meta} if repo_meta else {},
                feedback_by_key={issue_key: fb_status} if fb_status else {},
                include_uncertain=True,
                max_results=1,
            )

            return ranked[0] if ranked else None

    async def refresh_batch(self, issue_keys: Sequence[str]) -> tuple[int, int]:
        """Batch refresh multiple issues within rate budget."""
        refreshed = 0
        for key in issue_keys[:20]:
            parts = key.split("#")
            if len(parts) != 2:
                continue
            repo_part, num_str = parts
            repo_tokens = repo_part.split("/")
            if len(repo_tokens) != 2 or not num_str.isdigit():
                continue
            owner, repo = repo_tokens
            number = int(num_str)
            try:
                opp = await self.get_or_refresh_opportunity(owner, repo, number)
                if opp is not None:
                    refreshed += 1
            except Exception as exc:
                logger.warning("Error refreshing issue %s: %s", key, exc)

        return refreshed, len(issue_keys)
