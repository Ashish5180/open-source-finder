# Learning Log — Open-Source Contribution Opportunity Finder (CareerVerse PoC 07)

## Windowed Pagination with Safe Bounds & Multi-Predicate Filtering — 2026-10-27

**What was used:** A windowed, accessible pagination component with dynamic page-size controls, clamped safe page-index derivations, and an expandable multi-predicate filtering toolbar (assignment status, PR presence, minimum score threshold, candidate state, and topic tags).
**Why this over alternatives:** Rendering dozens of complex opportunity cards simultaneously causes DOM bloat and scroll fatigue. Slicing with client-side windowed pagination keeps render cycles instant while ensuring user filters automatically clamp `currentPage` to prevent displaying out-of-bounds empty views.
**Alternatives considered:** Infinite scroll (makes footer actions unreachable and disorients candidate scanning) or server-side pagination with frequent roundtrips (unnecessarily consumes scarce GitHub API quotas when cached results already reside in memory).
**Core concept to remember:** When implementing client-side pagination over dynamic filtered lists, always derive `safeCurrentPage = Math.min(currentPage, totalPages)` and reset `currentPage` to 1 whenever filtering predicates change, preventing phantom empty states.

---

## Sticky Action Dock & Modern Container Scrollbars (`scrollbar-color` / `scrollbar-width`) — 2026-10-25

**What was used:** An isolated vertical scroll container using standard CSS `scrollbar-color` and `scrollbar-width: thin` with webkit fallbacks, combined with a `sticky bottom-0` glassmorphic action footer hosting the primary CTA with keyboard accelerator (`Cmd+Enter`).
**Why this over alternatives:** In extensive filter sidebars, forcing the entire page to scroll pushes the primary submission button below the viewport fold, creating cognitive fatigue. An independent scroll container keeps the page structure stable while the sticky footer ensures the search action remains immediately accessible regardless of scroll position.
**Alternatives considered:** Floating fixed action buttons outside the card (disjointed visual hierarchy) or duplicating the search button at both the top and bottom of the form (cluttered UI).
**Core concept to remember:** Modern CSS standards allow customizable, cross-browser scrollbars natively without heavy JavaScript libraries (`perfect-scrollbar`). Sticky docks (`position: sticky; bottom: 0`) inside scrollable flex columns provide an elegant pattern for keeping high-intent CTAs within immediate reach as forms grow.

---

## SQLite WAL mode + Async SQLAlchemy 2.0 with UTC coercion — 2026-10-25

**What was used:** SQLite configured with Write-Ahead Logging (`PRAGMA journal_mode=WAL`), a 30s busy timeout, async engine via `aiosqlite`, and a defensive helper `_ensure_utc()` to coerce naive datetime objects back to UTC upon reload.
**Why this over alternatives:** SQLite WAL mode allows concurrent readers to operate without blocking concurrent writers, avoiding the common "database is locked" errors during background refreshes. Coercing timestamps is essential because SQLite stores datetimes as plain text strings, stripping timezone awareness upon retrieval.
**Alternatives considered:** PostgreSQL was considered, but added unnecessary deployment complexity and external container dependencies for a single-node local developer tool; in-memory SQLite lost state across process restarts.
**Core concept to remember:** SQLite is single-writer per file, but WAL mode moves writes to a separate `-wal` log file so reads don't block writes. Always enforce explicit timezone awareness in Python when doing datetime math on datetimes retrieved from databases that don't natively store offsets.

---

## Single-Flight Key Lock Registry (`asyncio.Lock()` per key) — 2026-10-25

**What was used:** An in-memory dictionary of `asyncio.Lock` instances keyed by query identifier (`candidate_profile_hash` or `owner/repo#number`), ensuring concurrent requests for the exact same resource await the first execution.
**Why this over alternatives:** When multiple frontend tabs or rapid user clicks fire searches for the same criteria simultaneously, single-flight locking coalesces them into one upstream GitHub API call, conserving rate budget and preventing race conditions in SQLite upserts.
**Alternatives considered:** Distributed locks with Redis (rejected due to zero external service constraint) or letting requests duplicate and relying on database unique constraints (wasted scarce GitHub API rate limit tokens).
**Core concept to remember:** The single-flight pattern deduplicates concurrent identical work at the application tier before it hits external APIs or persistence layers, dramatically reducing egress quota consumption under load spikes.

---

## Deterministic Multi-Factor Ranking Engine vs Black-Box LLMs — 2026-10-25

**What was used:** A transparent, weighted composite scoring engine (`v1.0.0`) evaluating candidate fit (30%), actionability (25%), repository health (25%), and freshness (20% with bot penalty), paired with deterministic tie-breaking (composite score -> activity timestamp -> issue number).
**Why this over alternatives:** Guarantees 100% reproducible rankings and 0% hallucinated reasons. When an issue is ranked high, the explanation cites only verified metadata (labels, commit frequency, checklist items, license), completely eliminating misleading or fabricated guidance.
**Alternatives considered:** LLM zero-shot reranking (prompting a model to rank issues) was rejected because it introduces non-deterministic outputs, API latency (2-5s per batch), high costs, and a propensity to hallucinate reasons that don't exist in the issue body.
**Core concept to remember:** Start with auditable deterministic heuristics before reaching for ML or LLMs. A heuristic system provides an exact baseline, explainable outputs, zero API invocation costs, and microseconds-level latency.

---

## ETag / 304 Conditional Requests & Rate Budget Tracker — 2026-10-25

**What was used:** Storing the `ETag` HTTP response header in SQLite alongside each issue/repo record, and sending `If-None-Match: <etag>` on subsequent fetch requests.
**Why this over alternatives:** GitHub does not count `304 Not Modified` responses against your hourly rate limit quota (or counts them with negligible cost), allowing CareerVerse to recheck cached issues frequently without draining the user's hourly quota.
**Alternatives considered:** Pure time-based cache expiration (TTL) without conditional requests (risk of serving stale data or wasting requests fetching unchanged issues).
**Core concept to remember:** Conditional HTTP requests (`ETag` / `If-None-Match`) allow clients to verify freshness with upstream servers without paying the payload size or API rate-limit penalties of full transfers.

---

## Frontend AbortController & Monotonic Request ID Race Protection — 2026-10-25

**What was used:** React `useRef` holding an active `AbortController` and an incrementing `requestId` integer for every search submission.
**Why this over alternatives:** When a user updates filter chips quickly (e.g. toggles Python, then Go, then Rust), an earlier slow network request could arrive *after* a later fast request, causing the UI to display stale results. Cancelling previous requests and discarding responses with stale request IDs guarantees UI consistency.
**Alternatives considered:** Debouncing inputs alone (helps reduce request volume, but doesn't solve out-of-order response arrivals over variable network latencies).
**Core concept to remember:** In asynchronous user interfaces, requests can complete out of order. Always cancel obsolete network calls using `AbortController` and tag async responses with monotonic sequence IDs to prevent stale state overwrites.
