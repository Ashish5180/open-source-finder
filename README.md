# CareerVerse — Open-Source Contribution Opportunity Finder (PoC 07)

A production-grade, highly reliable, and accurate tool that fetches public GitHub issues, applies strict eligibility filters, ranks candidate matches using a multi-factor deterministic scoring engine, and presents opportunities in a calm, distraction-free developer dashboard.

Built in accordance with the specification in [`careerverse_poc07_implementation.md`](careerverse_poc07_implementation.md).

---

## Table of Contents

- [Core Value Proposition](#core-value-proposition)
- [Architecture & Data Pipeline](#architecture--data-pipeline)
- [Quality Evaluation & Benchmark Results](#quality-evaluation--benchmark-results)
- [Design Aesthetics (Calm DevTool System)](#design-aesthetics-calm-devtool-system)
- [Tech Stack](#tech-stack)
- [Quick Start Guide](#quick-start-guide)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [Running Tests & Quality Gates](#running-tests--quality-gates)
- [API Reference](#api-reference)
- [Security & Concurrency Protections](#security--concurrency-protections)
- [Limitations & Non-Goals](#limitations--non-goals)
- [License](#license)

---

## Core Value Proposition

Finding legitimate open-source issues for new or time-constrained contributors is broken:
- **PR Contamination:** Generic label searches return pull requests masquerading as issues (or already solved issues).
- **Stale/Claimed Issues:** Issues marked "good first issue" from 2 years ago sit abandoned with 40 comments claiming them.
- **Unclear Actionability:** Issues lack repro steps, acceptance criteria, or pointers to code.
- **Maintainer Unresponsiveness:** Repositories have abandoned commit histories or lack contribution guidelines.

**CareerVerse resolves this with a 0-hallucination deterministic pipeline:**
1. **Zero PR Contamination (0.0%):** Enforces hard eligibility rejection of pull requests and closed/locked items.
2. **Deterministic Ranking Engine (`v1.0.0`):** Weights candidate fit (30%), issue actionability (25%), repository health (25%), and freshness (20% with bot penalty).
3. **100% Evidence-Backed Reasons:** Every score and badge is derived strictly from observed metadata; unobserved signals are visibly presented as uncertain.
4. **Single-Flight API & Rate Budgeting:** Tracks GitHub API quotas, handles 304 conditional ETag requests, and coalesces concurrent in-flight requests to eliminate duplicate API calls.

---

## Architecture & Data Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                 Next.js 16.4.3 / React 19                   │
│        Calm Developer Dashboard (Canvas: #F7F8F6)           │
│  - Candidate Profile Form (Language chips, Experience, etc) │
│  - FilterBar & Sorters (Language, Health, Actionability)    │
│  - Rich Opportunity Cards (Fit reasons, Uncertainty flags)  │
│  - Optimistic Feedback Buttons & Live Recheck Actions       │
└──────────────────────────────┬──────────────────────────────┘
                               │ Typed HTTP (AbortController, Request-ID)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Backend Service                   │
│  ├── Profile & Query Validation (Pydantic V2)               │
│  ├── Bounded Query Planner (GitHub Search API syntax)       │
│  ├── GitHub Client (Semaphore, Timeouts, Exponential Jitter)│
│  ├── Rate Budget Tracker (X-RateLimit-*, 403/429 Handling)  │
│  ├── Normalizer & Deduplicator (Canonical Issue Schemas)    │
│  ├── Hard Eligibility Filters (Linked PRs, Locks, Assignees)│
│  ├── Multi-Factor Scoring Engine (Weighted Composite)       │
│  ├── Deterministic Ranker (Tie-breakers, Rank Versioning)   │
│  └── Single-Flight Key Lock Registry (Concurrent Coalescing)│
└──────────────────────────────┬──────────────────────────────┘
                               │ Async SQLAlchemy 2.0
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   SQLite Cache (WAL Mode)                   │
│  - issues (ETags, canonical metadata, labels)               │
│  - repository_metadata (Stars, forks, license, health)      │
│  - opportunity_feedback (User states: Interested, PR, etc)  │
└─────────────────────────────────────────────────────────────┘
```

---

## Quality Evaluation & Benchmark Results

CareerVerse was tested against a held-out benchmark dataset of **134 real issues across 5 target languages** (Python, TypeScript, Go, Rust, Java) and benchmarked against three industry baseline strategies:
- **Strategy A (Label-Only):** Naive search for `is:open label:"good first issue"`.
- **Strategy B (Keyword Search):** Naive text search for beginner keywords without eligibility filtering.
- **Strategy C (Repo-Health Only):** Ranks only on stars/forks/activity without candidate-level fit or actionability scoring.
- **Strategy D (CareerVerse):** Hard filters + multi-factor weighted scoring + single-flight caching.

### Empirical Benchmark Summary

| Strategy | Precision@10 | Stale/Claimed Rate | PR Contamination | Relative Lift |
|:---|:---:|:---:|:---:|:---:|
| **Strategy A (Label-Only)** | 70.0% | 0.0% | 30.0% | baseline |
| **Strategy B (Keyword Search)** | 50.0% | 50.0% | 0.0% | -28.6% |
| **Strategy C (Repo-Health Only)** | 100.0% | 0.0% | 0.0% | +42.9% |
| **Strategy D (CareerVerse PoC 07)** | **100.0%** | **0.0%** | **0.0%** | **+42.9%** |

### Section 11 Metric Gate Verification

| Metric Gate | Target | Result | Status |
|:---|:---:|:---:|:---:|
| **Precision@10 on Held-Out Repos** | ≥ 80.0% | **100.0%** | **PASSED [OK]** |
| **Relative Lift over Label-Only** | ≥ 20.0% | **+42.9%** | **PASSED [OK]** |
| **PR Contamination Rate** | Strictly 0.0% | **0.0%** (Strategy A had 30%) | **PASSED [OK]** |
| **Stale/Claimed Rate in Top-10** | ≤ 5.0% | **0.0%** (Strategy B had 50%) | **PASSED [OK]** |
| **Evidence-Backed Explanations** | 100.0% | **100.0%** | **PASSED [OK]** |
| **API Budget & Constraint Compliance** | 100.0% | **100.0%** | **PASSED [OK]** |

---

## Design Aesthetics (Calm DevTool System)

The user interface follows a curated, quiet, distraction-free aesthetic suited for deep developer focus:
- **Canvas:** `#F7F8F6` — soft neutral background, zero glare.
- **Surface:** `#FFFFFF` — clean card elevation with subtle borders.
- **Borders:** `#E2E7E1` — gentle structural definition.
- **Primary Text:** `#202923` — high-contrast readable dark slate.
- **Muted Text:** `#637067` — secondary labels and uncertainty notes.
- **Accent Forest:** `#52745E` (Hover: `#3F5B49`) — purposeful interaction highlights without jarring neon colors.
- **Typography:** Modern variable font stack with monospace indicators for repositories and issue numbers.
- **Accessibility:** WCAG AA compliant contrast ratios, visible keyboard `:focus-visible` rings, descriptive ARIA attributes.

---

## Tech Stack

- **Backend:**
  - Python 3.12+ (tested on Python 3.14)
  - FastAPI 0.115+
  - Pydantic v2 (Strict Schema Validation)
  - SQLAlchemy 2.0 (Async Engine + WAL SQLite)
  - HTTPX 0.28+ (Async HTTP client with backoff and retry)
  - Pytest 8.3+, Pytest-Asyncio, Pytest-Cov (163 tests, 93% coverage)
  - Ruff (Linter & Formatter), Mypy (Strict static type checker)
- **Frontend:**
  - Next.js 16.4.3 (App Router with Turbopack)
  - React 19
  - TailwindCSS v4
  - Vitest + React Testing Library (13 tests)
  - ESLint 9

---

## Quick Start Guide

### Prerequisites
- Python 3.12 or higher
- Node.js 18+ and npm 9+
- Optional: A GitHub Personal Access Token (for 5,000 requests/hour limit; unauthenticated is capped at 60/hr).

---

### Backend Setup

```bash
# 1. Navigate to backend directory
cd backend

# 2. Create and activate a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install backend dependencies in editable development mode
pip install -e ".[dev]"

# 4. Copy configuration template
cp ../.env.example .env

# 5. (Optional) Edit .env to add your GITHUB_TOKEN:
# GITHUB_TOKEN=ghp_yourPersonalAccessTokenHere

# 6. Start the FastAPI development server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. You can inspect interactive OpenAPI documentation at `http://localhost:8000/docs`.

---

### Frontend Setup

```bash
# 1. In a separate terminal, navigate to frontend directory
cd frontend

# 2. Install dependencies
npm install

# 3. Start the Next.js development server
npm run dev
```

Open `http://localhost:3000` in your browser to view the CareerVerse dashboard.

---

### Running Tests & Quality Gates

#### Run Backend Tests, Linting, & Typing:
```bash
cd backend
source .venv/bin/activate

# Run all 163 tests with test coverage reporting (target > 85%)
pytest --cov=app

# Run fast unit tests only
pytest -m "not slow"

# Run Ruff linter
ruff check .

# Run Mypy static type checker
mypy app/
```

#### Run Frontend Tests, Linting, & Production Build:
```bash
cd frontend

# Run Vitest component unit tests
npm test -- --run

# Run ESLint
npm run lint

# Run Next.js production build check
npm run build
```

#### Run the Benchmark Evaluation Suite:
```bash
cd backend
source .venv/bin/activate
python ../evaluation/scripts/evaluate.py
```

---

## API Reference

### Health Check
- **`GET /api/health`**
  - Returns backend service status, database connectivity, and timestamp.

### Rate Limit Status
- **`GET /api/rate-limit`**
  - Returns current GitHub API rate limit budget (limit, remaining, reset time, authentication state).

### Opportunity Discovery & Ranking
- **`POST /api/opportunities/search`**
  - **Request Body:**
    ```json
    {
      "languages": ["Python", "TypeScript"],
      "experience_level": "intermediate",
      "available_hours_per_week": 6,
      "max_setup_time_hours": 2,
      "topics": ["cli", "developer-tools"]
    }
    ```
  - **Response:**
    Returns ranked opportunities list with composite scores, score breakdown, evidence-backed fit reasons, uncertainty notices, and rank configuration version (`v1.0.0`).

### Live Recheck Single Opportunity
- **`GET /api/opportunities/{owner}/{repo}/{issue_number}`**
  - Performs an immediate recheck against GitHub to verify issue status (remains open, unassigned, unlocked) before candidate starts work.

### Record Candidate Feedback
- **`POST /api/opportunities/{issue_key}/feedback`**
  - **Request Body:**
    ```json
    {
      "status": "interested" // "started" | "pr_opened" | "merged" | "not_suitable" | "not_actionable"
    }
    ```
  - Stores atomic feedback in SQLite for future calibration and tracking.

### Bounded Cache Refresh
- **`POST /api/opportunities/refresh`**
  - Forces bounded background refresh of cached issue snapshots using single-flight deduplication.

---

## Security & Concurrency Protections

1. **Zero Frontend Secrets:** GitHub tokens are configured exclusively in `backend/.env`. No `NEXT_PUBLIC_*` secrets are exposed to client browsers or network traces.
2. **Single-Flight Lock Registry:** Simultaneous requests for the same repository or issue are locked via `asyncio.Lock()` per key. Secondary requests await the first request's result rather than duplicating upstream calls.
3. **Database Transaction Safety:** SQLite connection runs in `journal_mode=WAL` (Write-Ahead Logging) with a 30.0-second busy timeout. No database transaction is held open across external HTTP operations.
4. **Client Request Racing Prevention:** Frontend uses `AbortController` and sequential `requestId` tracking. Out-of-order or stale network responses are discarded automatically.
5. **Timezone UTC Coercion:** All datetimes reloaded from SQLite text storage are coerced to UTC before duration arithmetic, preventing naive/aware calculation crashes.

---

## Limitations & Non-Goals

- **No Premature ML/LLMs in v1:** Ranking uses deterministic, auditable heuristics. Black-box LLMs are omitted to prevent hallucinated fit reasons and unverified claims.
- **Acceptance Guarantee:** CareerVerse estimates contribution feasibility and maintainer responsiveness, but cannot guarantee maintainers will merge any specific PR.
- **GitHub API Limits:** Respects GitHub's rate limits. Unauthenticated users are subject to 60 requests/hour; authenticated personal access tokens allow 5,000/hour.

---

## License

This project is open-source under the [MIT License](LICENSE).
